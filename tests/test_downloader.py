#!/usr/bin/env python3
"""Tests for Kick downloader - TDD approach."""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

class TestKickDownloader:
    """Test suite for Kick downloader."""
    
    def test_downloader_creates_output_directory(self):
        """Downloader should create output dir if not exists."""
        from downloader import KickDownloader
        
        test_dir = "/tmp/kick-test"
        dl = KickDownloader(output_dir=test_dir)
        
        assert Path(test_dir).exists()
        # Cleanup
        import shutil
        shutil.rmtree(test_dir)
    
    def test_downloader_validates_channel_format(self):
        """Channel should be validated before download."""
        from downloader import KickDownloader
        
        dl = KickDownloader()
        # Test with invalid channel
        # Should return None or raise error
        result = dl.get_stream_url("invalid!@#")
        assert result is None
    
    def test_downloader_list_downloaded_returns_list(self):
        """Should return list of downloaded files."""
        from downloader import KickDownloader
        
        dl = KickDownloader(output_dir="/tmp/kick-empty")
        Path("/tmp/kick-empty").mkdir(parents=True, exist_ok=True)
        
        files = dl.list_downloaded()
        assert isinstance(files, list)
        
        # Cleanup
        import shutil
        shutil.rmtree("/tmp/kick-empty")

if __name__ == "__main__":
    pytest.main([__file__, "-v"])