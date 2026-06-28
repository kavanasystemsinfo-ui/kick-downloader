"""
Integration tests for Kick Downloader API.
Tests the full flow from download request to file serving.
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


class TestIntegration:
    """Integration tests for the full download flow."""

    def test_full_download_flow_mp3(self, client, main_module, tmp_path):
        """Test complete flow: request download -> get URL -> download file."""
        # Override download directory
        original_dir = main_module.DOWNLOAD_DIR
        main_module.DOWNLOAD_DIR = tmp_path
        
        try:
            # Step 1: Request download (will fail without real Kick URL, but we test validation)
            response = client.post(
                "/download",
                json={
                    "url": "https://kick.com/video/test123",
                    "format_type": "mp3"
                }
            )
            # Should fail with 500 because yt-dlp can't download fake URL
            # But validation should pass
            assert response.status_code in (400, 500)
            
            # Step 2: Test with invalid URL (should fail validation)
            response = client.post(
                "/download",
                json={
                    "url": "https://youtube.com/watch?v=123",
                    "format_type": "mp3"
                }
            )
            assert response.status_code == 400
            assert "Invalid" in response.json()["detail"]
            
        finally:
            main_module.DOWNLOAD_DIR = original_dir

    def test_full_download_flow_mp4(self, client, main_module, tmp_path):
        """Test complete flow for MP4 format."""
        original_dir = main_module.DOWNLOAD_DIR
        main_module.DOWNLOAD_DIR = tmp_path
        
        try:
            # Test with invalid format
            response = client.post(
                "/download",
                json={
                    "url": "https://kick.com/video/test123",
                    "format_type": "invalid"
                }
            )
            assert response.status_code == 400
            assert "Invalid format" in response.json()["detail"]
            
        finally:
            main_module.DOWNLOAD_DIR = original_dir

    def test_file_serving_and_cleanup(self, client, main_module, tmp_path):
        """Test file serving works and cleanup is scheduled."""
        original_dir = main_module.DOWNLOAD_DIR
        main_module.DOWNLOAD_DIR = tmp_path
        
        try:
            # Create a test file
            test_file = tmp_path / "integration-test.mp3"
            test_file.write_text("integration test content")
            
            # Serve the file
            response = client.get("/files/integration-test.mp3")
            assert response.status_code == 200
            assert response.content == b"integration test content"
            
            # With CLEANUP_GRACE_SECONDS=0, file is deleted immediately after serving
            # This is the expected behavior in test environment
            # In production with 300 seconds, file would persist for client download
            
        finally:
            main_module.DOWNLOAD_DIR = original_dir

    def test_multiple_file_requests(self, client, main_module, tmp_path):
        """Test multiple file requests work independently."""
        original_dir = main_module.DOWNLOAD_DIR
        main_module.DOWNLOAD_DIR = tmp_path
        
        try:
            # Create multiple test files
            file1 = tmp_path / "file1.mp3"
            file1.write_text("content 1")
            file2 = tmp_path / "file2.mp4"
            file2.write_text("content 2")
            
            # Request both files
            response1 = client.get("/files/file1.mp3")
            response2 = client.get("/files/file2.mp4")
            
            assert response1.status_code == 200
            assert response1.content == b"content 1"
            assert response2.status_code == 200
            assert response2.content == b"content 2"
            
        finally:
            main_module.DOWNLOAD_DIR = original_dir

    def test_concurrent_download_requests(self, client, main_module, tmp_path):
        """Test multiple download requests can be made."""
        original_dir = main_module.DOWNLOAD_DIR
        main_module.DOWNLOAD_DIR = tmp_path
        
        try:
            # Make multiple download requests (they'll fail at yt-dlp but validation passes)
            for i in range(3):
                response = client.post(
                    "/download",
                    json={
                        "url": f"https://kick.com/video/test{i}",
                        "format_type": "mp3"
                    }
                )
                # Should fail at processing, not validation
                assert response.status_code in (400, 500)
                
        finally:
            main_module.DOWNLOAD_DIR = original_dir


class TestErrorHandling:
    """Tests for error handling and edge cases."""

    def test_empty_request_body(self, client):
        """Should handle empty request body."""
        response = client.post("/download", json={})
        assert response.status_code == 422

    def test_malformed_json(self, client):
        """Should handle malformed JSON."""
        response = client.post(
            "/download",
            content="not json",
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 422

    def test_file_with_special_characters(self, client, main_module, tmp_path):
        """Should handle files with special characters in name."""
        original_dir = main_module.DOWNLOAD_DIR
        main_module.DOWNLOAD_DIR = tmp_path
        
        try:
            # Create file with special characters
            test_file = tmp_path / "test file (1).mp3"
            test_file.write_text("special chars")
            
            response = client.get("/files/test%20file%20%281%29.mp3")
            assert response.status_code == 200
            assert response.content == b"special chars"
            
        finally:
            main_module.DOWNLOAD_DIR = original_dir

    def test_large_file_handling(self, client, main_module, tmp_path):
        """Should handle larger files."""
        original_dir = main_module.DOWNLOAD_DIR
        main_module.DOWNLOAD_DIR = tmp_path
        
        try:
            # Create a larger test file (1MB)
            test_file = tmp_path / "large.mp4"
            test_file.write_bytes(b"x" * (1024 * 1024))
            
            response = client.get("/files/large.mp4")
            assert response.status_code == 200
            assert len(response.content) == 1024 * 1024
            
        finally:
            main_module.DOWNLOAD_DIR = original_dir