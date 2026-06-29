#!/usr/bin/env python3
"""FastAPI server for Kick video downloading."""

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pathlib import Path
import uuid
import os

from downloader import KickDownloader

app = FastAPI(title="Kick Downloader API")

# CORS para GitHub Pages
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://kavanasystemsinfo-ui.github.io",
        "http://localhost:8000",
        "http://127.0.0.1:8000"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)
DOWNLOAD_DIR = Path("/opt/kick-downloader/downloads")
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Servir frontend estático
STATIC_DIR = Path(__file__).parent.parent / "static"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

@app.get("/")
async def root():
    """Serve the web interface."""
    index = STATIC_DIR / "index.html"
    if index.exists():
        return FileResponse(str(index))
    return {"message": "Kick Downloader API - visit /docs for Swagger"}

class DownloadRequest(BaseModel):
    url: str
    format: str = "mp4"  # mp4, mp3

@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok", "service": "kick-downloader"}

@app.post("/download")
async def download_video(request: DownloadRequest):
    """Download Kick video using yt_dlp with impersonation."""
    # Validate URL
    if "kick.com" not in request.url:
        raise HTTPException(400, "Invalid Kick URL")
    
    try:
        dl = KickDownloader(output_dir=str(DOWNLOAD_DIR))
        result = dl.download_stream(request.url, quality="best")
        
        if result.get("status") == "error":
            raise HTTPException(500, result.get("message", "Download failed"))
        
        file_path = Path(result["file_path"])
        return {
            "status": "success",
            "file_url": f"/files/{file_path.name}",
            "file_path": str(file_path)
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Download error: {str(e)}")

@app.get("/files/{filename}")
async def get_file(filename: str):
    """Serve downloaded file for download."""
    file_path = DOWNLOAD_DIR / filename
    if not file_path.exists():
        raise HTTPException(404, "File not found")
    return FileResponse(
        str(file_path),
        media_type="application/octet-stream",
        filename=filename
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)