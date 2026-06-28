"""
Kick Downloader API - Backend service for downloading Kick.com videos.
"""

import os
import re
import uuid
from pathlib import Path

from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# Configuration
DOWNLOAD_DIR = Path("./downloads")
# Allow override via environment variable for testing
CLEANUP_GRACE_SECONDS = int(os.environ.get("CLEANUP_GRACE_SECONDS", "300"))

# Rate limiting configuration
RATE_LIMIT_REQUESTS = int(os.environ.get("RATE_LIMIT_REQUESTS", "10"))
RATE_LIMIT_WINDOW = os.environ.get("RATE_LIMIT_WINDOW", "minute")

# Ensure download directory exists
DOWNLOAD_DIR.mkdir(exist_ok=True)


def validate_kick_url(url: str) -> bool:
    """Validate that URL is a valid Kick.com video URL."""
    if not url:
        return False
    pattern = r"^https?://(www\.)?kick\.com/(video|videos)/.+$"
    return bool(re.match(pattern, url))


def get_file_extension(format_type: str) -> str:
    """Get file extension based on format type."""
    if format_type == "mp3":
        return "mp3"
    return "mp4"


class DownloadRequest(BaseModel):
    """Request model for download endpoint."""
    url: str
    format_type: str  # "mp3" or "mp4"


# In-memory file tracking (for production, use Redis or database)
file_registry: dict[str, str] = {}


def schedule_cleanup(file_path: str) -> None:
    """Schedule file cleanup after grace period."""
    import time
    time.sleep(CLEANUP_GRACE_SECONDS)
    if os.path.exists(file_path):
        os.remove(file_path)


# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)

app = FastAPI(title="Kick Downloader API")

# Add rate limiter to app state
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


@app.post("/download")
@limiter.limit(f"{RATE_LIMIT_REQUESTS}/{RATE_LIMIT_WINDOW}")
def process_kick_video(request: Request, download_request: DownloadRequest):
    """
    Process a Kick.com video URL and return download link.
    
    Args:
        request: FastAPI request (for rate limiting)
        download_request: DownloadRequest with url and format_type
        
    Returns:
        JSON with status and download_url
    """
    # Validate URL
    if not validate_kick_url(download_request.url):
        raise HTTPException(status_code=400, detail="Invalid Kick.com URL")
    
    # Validate format type
    if download_request.format_type not in ("mp3", "mp4"):
        raise HTTPException(status_code=400, detail="Invalid format type. Use 'mp3' or 'mp4'")
    
    # Generate unique file ID
    file_id = str(uuid.uuid4())
    ext = get_file_extension(download_request.format_type)
    output_template = str(DOWNLOAD_DIR / f"{file_id}.%(ext)s")
    
    # yt-dlp options
    ydl_opts = {
        "outtmpl": output_template,
        "quiet": True,
        "no_warnings": True,
    }
    
    if download_request.format_type == "mp3":
        ydl_opts.update({
            "format": "bestaudio/best",
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }],
        })
    else:
        ydl_opts.update({
            "format": "bestvideo+bestaudio/best",
            "merge_output_format": "mp4",
        })
    
    try:
        import yt_dlp
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.extract_info(download_request.url, download=True)
        
        final_filename = f"{file_id}.{ext}"
        file_path = DOWNLOAD_DIR / final_filename
        file_registry[file_id] = str(file_path)
        
        return {
            "status": "success",
            "download_url": f"/files/{final_filename}"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}")


@app.get("/files/{file_name}")
def get_file(file_name: str, background_tasks: BackgroundTasks):
    """
    Serve a processed file for download.
    
    Args:
        file_name: Name of the file to download
        background_tasks: FastAPI background tasks for cleanup
        
    Returns:
        FileResponse with the file
    """
    file_path = DOWNLOAD_DIR / file_name
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found or already downloaded")
    
    # Schedule cleanup after response
    background_tasks.add_task(schedule_cleanup, str(file_path))
    
    return FileResponse(
        path=str(file_path),
        filename=file_name,
        media_type="application/octet-stream"
    )


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}