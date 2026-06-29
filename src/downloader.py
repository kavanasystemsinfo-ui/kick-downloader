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
    
    def download_stream(self, channel: str, quality: str = "worst", dry_run: bool = False, output_format: str = "mp4") -> dict:
        """Download stream from channel using yt_dlp module.
        
        Args:
            channel: Kick URL or channel name
            quality: Video quality (best, worst)
            dry_run: If True, validate URL only without downloading
            output_format: mp4 (video) or mp3 (audio only)
        Returns:
            dict with status and metadata
        """
        import uuid
        import traceback
        
        # Validate the URL
        if "kick.com" not in channel:
            raise ValueError("Invalid Kick URL")
        
        file_id = str(uuid.uuid4())[:8]
        
        if dry_run:
            return {"status": "dry_run", "channel": channel, "quality": quality}
        
        # Configure yt-dlp options with impersonation
        from yt_dlp.networking.impersonate import ImpersonateTarget
        
        output_path = self.output_dir / f"{file_id}.%(ext)s"
        
        if output_format == "mp3":
            # Audio only - much smaller, 100-300 MB for 4h stream
            ydl_opts = {
                'format': 'bestaudio/best',
                'outtmpl': str(output_path),
                'quiet': False,
                'no_warnings': False,
                'extract_flat': False,
                'impersonate': ImpersonateTarget('chrome'),
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                }],
            }
        else:
            # Video with quality selection
            format_str = "worstvideo+worstaudio/worst" if quality == "worst" else "bestvideo+bestaudio/best"
            ydl_opts = {
                'format': format_str,
                'outtmpl': str(output_path),
                'quiet': False,
                'no_warnings': False,
                'extract_flat': False,
                'impersonate': ImpersonateTarget('chrome'),
            }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(channel, download=True)
                if info is None:
                    return {"status": "error", "message": "No info returned from yt-dlp"}
                
                # Get actual output file path
                actual_file = ydl.prepare_filename(info)
                if info.get('ext'):
                    actual_file = actual_file.replace('%(ext)s', info['ext'])
                
                # Find the actual file that was downloaded
                downloaded = list(self.output_dir.glob(f"{file_id}.*"))
                if downloaded:
                    actual_path = downloaded[0]
                    return {
                        "status": "success",
                        "file_path": str(actual_path),
                        "file_size": actual_path.stat().st_size,
                        "channel": channel
                    }
                
                return {"status": "error", "message": "File not found after download"}
                
        except yt_dlp.utils.DownloadError as e:
            msg = str(e) or (e.args[0] if e.args else 'Unknown error')
            if msg.startswith('ERROR: '):
                msg = msg[7:]
            return {"status": "error", "message": msg}
        except Exception as e:
            msg = str(e) or (e.args[0] if e.args else 'Unknown error')
            return {"status": "error", "message": f"Error: {msg}"}
    
    def list_downloaded(self) -> list:
        """List downloaded videos."""
        return list(self.output_dir.glob("*.mp4"))