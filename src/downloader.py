#!/usr/bin/env python3
"""Kick stream downloader - TDD approach + speed + progress."""

import yt_dlp
from pathlib import Path


class KickDownloader:
    """Download Kick streams with validation."""

    def __init__(self, output_dir: str = "/root/kick-downloader/data/videos"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def download_stream(
        self,
        channel: str,
        quality: str = "worst",
        dry_run: bool = False,
        output_format: str = "mp4",
        progress_callback: callable = None,
    ) -> dict:
        """Download stream with optional progress reporting.

        Args:
            channel: Kick URL
            quality: best/worst
            dry_run: validate only
            output_format: mp4/mp3
            progress_callback: func(progress_dict) called during download
        """
        import uuid

        if "kick.com" not in channel:
            raise ValueError("Invalid Kick URL")

        file_id = str(uuid.uuid4())[:8]

        if dry_run:
            return {"status": "dry_run", "channel": channel, "quality": quality}

        from yt_dlp.networking.impersonate import ImpersonateTarget

        output_path = self.output_dir / f"{file_id}.%(ext)s"

        # Progress hook for yt-dlp
        def progress_hook(d):
            if progress_callback:
                progress_callback({
                    "status": d.get("status", "downloading"),
                    "downloaded_bytes": d.get("downloaded_bytes", 0),
                    "total_bytes": d.get("total_bytes") or d.get("total_bytes_estimate", 0),
                    "speed": d.get("speed", 0),
                    "eta": d.get("eta", 0),
                    "percentage": d.get("_percent_str", "0%").strip(),
                    "speed_str": d.get("_speed_str", "").strip(),
                    "eta_str": d.get("_eta_str", "").strip(),
                    "file_id": file_id,
                })

        ydl_opts = {
            "outtmpl": str(output_path),
            "quiet": True,
            "no_warnings": True,
            "extract_flat": False,
            "impersonate": ImpersonateTarget("chrome"),
            "progress_hooks": [progress_hook],
            # Speed optimizations
            "throttledratelimit": 100000000,
            "concurrent_fragments": 5,
            "buffered": True,
            "fragment_retries": 5,
            "retries": 10,
            "skip_unavailable_fragments": True,
            "extractor_retries": 3,
            "file_access_retries": 5,
        }

        if output_format == "mp3":
            ydl_opts.update({
                "format": "bestaudio/best",
                "postprocessors": [{
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                }],
            })
        else:
            fmt = "worstvideo+worstaudio/worst" if quality == "worst" else "bestvideo+bestaudio/best"
            ydl_opts.update({"format": fmt})

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(channel, download=True)
                if info is None:
                    return {"status": "error", "message": "No info returned from yt-dlp"}

                downloaded = list(self.output_dir.glob(f"{file_id}.*"))
                if downloaded:
                    actual_path = downloaded[0]
                    return {
                        "status": "success",
                        "file_path": str(actual_path),
                        "file_size": actual_path.stat().st_size,
                        "channel": channel,
                    }
                return {"status": "error", "message": "File not found after download"}

        except yt_dlp.utils.DownloadError as e:
            msg = str(e) or (e.args[0] if e.args else "Unknown error")
            if msg.startswith("ERROR: "):
                msg = msg[7:]
            return {"status": "error", "message": msg}
        except Exception as e:
            return {"status": "error", "message": f"Error: {e}"}