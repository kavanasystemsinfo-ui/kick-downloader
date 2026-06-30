#!/usr/bin/env python3
"""FastAPI server for Kick video downloading with progress tracking."""

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pathlib import Path
import uuid
import os
import threading
import time

from downloader import KickDownloader

app = FastAPI(title="Kick Downloader API")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://kavanasystemsinfo-ui.github.io",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

DOWNLOAD_DIR = Path("/opt/kick-downloader/downloads")
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

STATIC_DIR = Path(__file__).parent.parent / "static"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# In-memory progress tracking
download_progress: dict[str, dict] = {}


class DownloadRequest(BaseModel):
    url: str
    format: str = "mp4"
    quality: str = "worst"


def background_download(job_id: str, url: str, fmt: str, quality: str):
    """Run download in background thread, updating progress dict."""
    def on_progress(p):
        download_progress[job_id] = p

    try:
        dl = KickDownloader(output_dir=str(DOWNLOAD_DIR))
        download_progress[job_id] = {
            "status": "starting",
            "percentage": "0%",
            "speed_str": "",
            "eta_str": "",
            "downloaded_bytes": 0,
            "total_bytes": 0,
        }

        result = dl.download_stream(
            url,
            quality=quality,
            output_format=fmt,
            progress_callback=on_progress,
        )

        if result.get("status") == "success":
            file_path = Path(result["file_path"])
            file_size = result.get("file_size", 0)
            file_size_mb = round(file_size / (1024 * 1024), 1) if file_size else 0
            download_progress[job_id] = {
                "status": "completed",
                "percentage": "100%",
                "speed_str": "",
                "eta_str": "",
                "file_url": f"/files/{file_path.name}",
                "file_name": file_path.name,
                "file_size_mb": file_size_mb,
                "downloaded_bytes": file_size,
                "total_bytes": file_size,
            }
        else:
            download_progress[job_id] = {
                "status": "error",
                "percentage": "0%",
                "error": result.get("message", "Unknown error"),
            }
    except Exception as e:
        download_progress[job_id] = {
            "status": "error",
            "percentage": "0%",
            "error": str(e),
        }


@app.get("/")
async def root():
    index = STATIC_DIR / "index.html"
    if index.exists():
        return FileResponse(str(index))
    return {"message": "Kick Downloader API - visit /docs for Swagger"}


@app.get("/health")
async def health():
    return {"status": "ok", "service": "kick-downloader"}


@app.post("/download")
async def download_video(request: DownloadRequest):
    """Start a download in background and return job_id immediately."""
    if "kick.com" not in request.url:
        raise HTTPException(400, "Invalid Kick URL")
    if request.format == "mp4":
        raise HTTPException(400, "MP4 deshabilitado temporalmente. Solo MP3 disponible.")

    job_id = str(uuid.uuid4())[:8]

    # Start download in background thread
    thread = threading.Thread(
        target=background_download,
        args=(job_id, request.url, request.format, request.quality),
        daemon=True,
    )
    thread.start()

    return {
        "status": "started",
        "job_id": job_id,
        "progress_url": f"/progress/{job_id}",
        "message": "Descarga iniciada. Consulta /progress/{job_id} para ver el avance.",
    }


@app.get("/progress/{job_id}")
async def get_progress(job_id: str):
    """Return current download progress."""
    progress = download_progress.get(job_id)
    if progress is None:
        # Check if expired but completed
        return {"status": "not_found", "job_id": job_id}

    # Clean up completed/error jobs older than 5 min
    if progress.get("status") in ("completed", "error"):
        # Return data but mark for cleanup after client sees it
        return progress

    return progress


@app.get("/files/{filename}")
async def get_file(filename: str):
    """Serve downloaded file."""
    file_path = DOWNLOAD_DIR / filename
    if not file_path.exists():
        raise HTTPException(404, "File not found")
    return FileResponse(
        str(file_path),
        media_type="application/octet-stream",
        filename=filename,
    )


# Periodic cleanup of old progress entries (runs every 5 min)
def cleanup_old_progress():
    while True:
        time.sleep(300)
        now = time.time()
        to_delete = []
        for job_id, prog in download_progress.items():
            if prog.get("status") in ("completed", "error"):
                to_delete.append(job_id)
        for jid in to_delete:
            download_progress.pop(jid, None)


cleanup_thread = threading.Thread(target=cleanup_old_progress, daemon=True)
cleanup_thread.start()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
