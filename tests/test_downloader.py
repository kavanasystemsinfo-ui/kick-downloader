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
        # Test with invalid channel - should raise error
        with pytest.raises(ValueError):
            dl.get_stream_url("invalid!@#")
    
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
    
    def test_download_stream_invalid_url_raises_error(self):
        """Should raise ValueError for invalid URL."""
        from downloader import KickDownloader
        
        dl = KickDownloader(output_dir="/tmp/kick-test-invalid")
        with pytest.raises(ValueError, match="Invalid"):
            dl.download_stream("not-a-valid-url")
        import shutil
        shutil.rmtree("/tmp/kick-test-invalid", ignore_errors=True)
    
    def test_download_stream_returns_dict(self):
        """download_stream should return a dict with status."""
        from downloader import KickDownloader
        
        dl = KickDownloader(output_dir="/tmp/kick-test-stream")
        result = dl.download_stream("https://kick.com/testchannel", dry_run=True)
        assert isinstance(result, dict)
        assert "status" in result
        import shutil
        shutil.rmtree("/tmp/kick-test-stream", ignore_errors=True)

if __name__ == "__main__":
    pytest.main([__file__, "-v"])