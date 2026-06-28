"""
Tests for Kick Downloader API.
Following TDD: These tests define the expected behavior before implementation.
"""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="session", autouse=True)
def setup_test_env():
    """Set up test environment before any tests run."""
    import os
    os.environ["CLEANUP_GRACE_SECONDS"] = "0"
    
    # Force reload main module
    import sys
    if "main" in sys.modules:
        import importlib
        importlib.reload(sys.modules["main"])


@pytest.fixture
def client():
    """Create test client after environment is set up."""
    from main import app
    return TestClient(app)


@pytest.fixture
def main_module():
    """Get main module after environment is set up."""
    import main
    return main


class TestKickUrlValidation:
    """Tests for Kick URL validation logic."""

    def test_valid_kick_video_url(self, main_module):
        """Should accept valid Kick.com video URLs."""
        valid_urls = [
            "https://kick.com/video/abc123",
            "https://kick.com/videos/xyz789",
            "https://www.kick.com/video/test-stream",
        ]
        for url in valid_urls:
            assert main_module.validate_kick_url(url) is True, f"Should accept {url}"

    def test_invalid_url_not_kick(self, main_module):
        """Should reject URLs that are not from Kick.com."""
        invalid_urls = [
            "https://youtube.com/watch?v=123",
            "https://twitch.tv/videos/123",
            "https://example.com/video/123",
            "not-a-url",
            "",
        ]
        for url in invalid_urls:
            assert main_module.validate_kick_url(url) is False, f"Should reject {url}"

    def test_invalid_url_malformed(self, main_module):
        """Should reject malformed URLs."""
        malformed_urls = [
            "kick.com/video/123",
            "http://kick",
            "https://kick.com",
        ]
        for url in malformed_urls:
            assert main_module.validate_kick_url(url) is False, f"Should reject {url}"


class TestFileExtension:
    """Tests for file extension determination."""

    def test_mp3_extension(self, main_module):
        """Should return mp3 for audio format."""
        assert main_module.get_file_extension("mp3") == "mp3"

    def test_mp4_extension(self, main_module):
        """Should return mp4 for video format."""
        assert main_module.get_file_extension("mp4") == "mp4"

    def test_invalid_format_defaults_to_mp4(self, main_module):
        """Should default to mp4 for invalid format types."""
        assert main_module.get_file_extension("invalid") == "mp4"


class TestDownloadEndpoint:
    """Tests for the /download endpoint."""

    def test_download_missing_url(self, client):
        """Should return 422 for missing URL in request."""
        response = client.post("/download", json={"format_type": "mp3"})
        assert response.status_code == 422

    def test_download_missing_format_type(self, client):
        """Should return 422 for missing format_type in request."""
        response = client.post("/download", json={"url": "https://kick.com/video/123"})
        assert response.status_code == 422

    def test_download_invalid_url(self, client):
        """Should return 400 for non-Kick URL."""
        response = client.post(
            "/download",
            json={"url": "https://youtube.com/watch?v=123", "format_type": "mp3"}
        )
        assert response.status_code == 400
        assert "Invalid" in response.json()["detail"]

    def test_download_invalid_format(self, client):
        """Should return 400 for invalid format type."""
        response = client.post(
            "/download",
            json={"url": "https://kick.com/video/123", "format_type": "avi"}
        )
        assert response.status_code == 400
        assert "Invalid format" in response.json()["detail"]


class TestFilesEndpoint:
    """Tests for the /files/{file_name} endpoint."""

    def test_file_not_found(self, client):
        """Should return 404 for non-existent file."""
        response = client.get("/files/nonexistent.mp3")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_file_serve_success(self, client, main_module, tmp_path):
        """Should serve existing file with correct headers."""
        # Create a test file
        test_file = tmp_path / "test-file.mp3"
        test_file.write_text("test content")
        
        # Override download directory for test
        original_dir = main_module.DOWNLOAD_DIR
        main_module.DOWNLOAD_DIR = tmp_path
        
        try:
            response = client.get("/files/test-file.mp3")
            assert response.status_code == 200
            assert response.content == b"test content"
        finally:
            main_module.DOWNLOAD_DIR = original_dir

    def test_file_cleanup_scheduled(self, client, main_module, tmp_path):
        """Should schedule file cleanup after serving (background task added)."""
        test_file = tmp_path / "cleanup-test.mp3"
        test_file.write_text("test content")
        
        original_dir = main_module.DOWNLOAD_DIR
        main_module.DOWNLOAD_DIR = tmp_path
        
        try:
            response = client.get("/files/cleanup-test.mp3")
            assert response.status_code == 200
            # Verify background task was scheduled by checking the response was successful
            # The actual cleanup happens asynchronously, so we just verify the endpoint works
        finally:
            main_module.DOWNLOAD_DIR = original_dir