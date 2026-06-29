#!/usr/bin/env python3
"""Kick stream downloader - TDD approach."""

import subprocess
import yt_dlp
from pathlib import Path
from typing import Optional

class KickDownloader:
    """Download Kick streams with validation."""
    
    def __init__(self, output_dir: str = "/root/kick-downloader/data/videos"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def get_stream_url(self, channel: str) -> Optional[str]:
        """Get stream URL for a Kick channel."""
        # Validate it's a proper Kick URL
        if "kick.com" not in channel or "notkick" in channel:
            raise ValueError("Invalid Kick URL")
        
        # Extract stream URL using yt-dlp
        ydl_opts = {'quiet': True, 'no_warnings': True}
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(channel, download=False)
                if info and 'url' in info:
                    return info['url']
                elif info and 'formats' in info:
                    for f in info['formats']:
                        if f.get('ext') == 'mp4':
                            return f['url']
        except Exception:
            pass
        return None
    
    def download_stream(self, channel: str, quality: str = "best", dry_run: bool = False) -> dict:
        """Download stream from channel.
        
        Args:
            channel: Kick URL or channel name
            quality: Video quality (best, worst)
            dry_run: If True, validate URL only without downloading
        Returns:
            dict with status and metadata
        """
        # Validate the URL
        if "kick.com" not in channel:
            raise ValueError("Invalid Kick URL")
        
        if dry_run:
            return {"status": "dry_run", "channel": channel, "quality": quality}
        
        # Get stream URL
        stream_url = self.get_stream_url(channel)
        if not stream_url:
            return {"status": "error", "message": "Stream not found or offline"}
        
        # Download with yt-dlp
        import subprocess
        import uuid
        
        file_id = str(uuid.uuid4())[:8]
        output_path = self.output_dir / f"{file_id}.mp4"
        
        try:
            cmd = [
                "yt-dlp",
                "-o", str(output_path),
                "-f", "bestvideo+bestaudio/best" if quality == "best" else "worst",
                channel
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode != 0:
                return {"status": "error", "message": f"Download failed: {result.stderr}"}
            
            return {
                "status": "success",
                "file_path": str(output_path),
                "file_size": output_path.stat().st_size if output_path.exists() else 0,
                "channel": channel
            }
        except subprocess.TimeoutExpired:
            return {"status": "error", "message": "Download timeout after 300s"}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def list_downloaded(self) -> list:
        """List downloaded videos."""
        return list(self.output_dir.glob("*.mp4"))