#!/usr/bin/env python3
"""RED: Test that will fail until yt-dlp integration is implemented."""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

class TestYTDLPDownload:
    """Test yt-dlp download functionality - RED phase."""
    
    def test_downloader_uses_yt_dlp_for_kick_urls(self):
        """Should extract stream URL using yt-dlp (will FAIL initially)."""
        from downloader import KickDownloader
        
        dl = KickDownloader()
        url = dl.get_stream_url("https://kick.com/teststream")
        assert url is None or "stream" in url.lower() or "m3u8" in url.lower()
    
    def test_downloader_validates_kick_url(self):
        """Should raise error for non-Kick URLs."""
        from downloader import KickDownloader
        
        dl = KickDownloader()
        with pytest.raises(ValueError):
            dl.get_stream_url("https://twitch.tv/channel")

if __name__ == "__main__":
    pytest.main([__file__, "-v"])