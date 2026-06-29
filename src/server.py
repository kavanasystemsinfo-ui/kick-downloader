#!/usr/bin/env python3
"""FastAPI server for Kick video downloading."""

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from pathlib import Path
import subprocess
import uuid
import os

app = FastAPI(title="Kick Downloader API")
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
    """Download and convert Kick video."""
    # Validate URL
    if "kick.com" not in request.url:
        raise HTTPException(400, "Invalid Kick URL")
    
    # Generate unique filename
    file_id = str(uuid.uuid4())[:8]
    output_file = DOWNLOAD_DIR / f"{file_id}.{request.format}"
    
    try:
        # Download with yt-dlp
        cmd = [
            "yt-dlp",
            "-o", str(output_file),
            "-f", "bestvideo+bestaudio/best" if request.format == "mp4" else "bestaudio",
            request.url
        ]
        
        if request.format == "mp3":
            cmd.extend(["--extract-audio", "--audio-format", "mp3"])
        
        result = subprocess.run(cmd, capture_output=True, timeout=300)
        
        if result.returncode != 0:
            raise HTTPException(500, f"Download failed: {result.stderr.decode()}")
        
        return {
            "status": "success",
            "file_url": f"/files/{output_file.name}",
            "file_path": str(output_file)
        }
    except subprocess.TimeoutExpired:
        raise HTTPException(500, "Download timeout")

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