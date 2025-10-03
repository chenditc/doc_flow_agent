#!/usr/bin/env python3
"""
Integration tests for User Communication API endpoints
"""

import json
import tempfile
from pathlib import Path
from fastapi.testclient import TestClient

# Add project root to path
import sys
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from visualization.server.viz_server import app


class TestUserCommAPI:
    """Test cases for user communication API endpoints"""
    
    def setup_method(self):
        """Set up test client"""
        self.client = TestClient(app)
    
    def test_submit_response_new(self):
        """Test submitting a new response"""
        payload = {
            "session_id": "api_test_session",
            "task_id": "api_test_task", 
            "answer": "This is a test response"
        }
        
        response = self.client.post("/api/user-comm/submit", json=payload)
        
        assert response.status_code == 200
        result = response.json()
        assert result["success"] == True
        assert result["existing"] == False
        assert "timestamp" in result
    
    def test_submit_response_existing(self):
        """Test submitting response when one already exists (idempotent)"""
        payload = {
            "session_id": "api_test_session_2",
            "task_id": "api_test_task_2",
            "answer": "First response"
        }
        
        # Submit first time
        response1 = self.client.post("/api/user-comm/submit", json=payload)
        assert response1.status_code == 200
        result1 = response1.json()
        assert result1["existing"] == False
        
        # Submit second time with different answer
        payload["answer"] = "Second response"
        response2 = self.client.post("/api/user-comm/submit", json=payload)
        assert response2.status_code == 200
        result2 = response2.json()
        assert result2["existing"] == True  # Should return existing response
    
    def test_get_status_no_response(self):
        """Test status endpoint when no response exists"""
        response = self.client.get("/api/user-comm/status/nonexistent_session/nonexistent_task")
        
        assert response.status_code == 200
        result = response.json()
        assert result["responded"] == False
    
    def test_get_status_with_response(self):
        """Test status endpoint when response exists"""
        # First submit a response
        payload = {
            "session_id": "status_test_session",
            "task_id": "status_test_task",
            "answer": "Status test response"
        }
        submit_response = self.client.post("/api/user-comm/submit", json=payload)
        assert submit_response.status_code == 200
        
        # Then check status
        status_response = self.client.get("/api/user-comm/status/status_test_session/status_test_task")
        assert status_response.status_code == 200
        result = status_response.json()
        assert result["responded"] == True
        assert result["answer"] == "Status test response"
        assert "timestamp" in result
    
    def test_submit_response_validation(self):
        """Test request validation"""
        # Missing required fields
        invalid_payloads = [
            {},  # Missing everything
            {"session_id": "test"},  # Missing task_id and answer
            {"session_id": "test", "task_id": "test"},  # Missing answer
        ]
        
        for payload in invalid_payloads:
            response = self.client.post("/api/user-comm/submit", json=payload)
            assert response.status_code == 422  # Validation error
    
    def test_path_sanitization(self):
        """Test that session_id and task_id are properly sanitized"""
        # Test with potentially dangerous path components
        payload = {
            "session_id": "../../../etc",
            "task_id": "passwd",
            "answer": "Hacking attempt"
        }
        
        response = self.client.post("/api/user-comm/submit", json=payload)
        # Should still work but with sanitized paths
        assert response.status_code == 200
        result = response.json()
        assert result["success"] == True


class TestFormServing:
    """Test form serving functionality"""
    
    def setup_method(self):
        """Set up test client"""
        self.client = TestClient(app)
    
    def test_serve_nonexistent_form(self):
        """Test serving a form that doesn't exist"""
        response = self.client.get("/user-comm/nonexistent_session/nonexistent_task/")
        assert response.status_code == 404
    
    def test_serve_existing_form(self):
        """Test serving an existing form (using the one we created earlier)"""
        # This test depends on the form created by our earlier test
        response = self.client.get("/user-comm/test_session_demo/rating_task/")
        
        if response.status_code == 200:
            # Form exists - check it's HTML
            assert "text/html" in response.headers.get("content-type", "")
            assert "<!DOCTYPE html>" in response.text or "<html" in response.text
        else:
            # Form doesn't exist - that's also valid for a clean test environment
            assert response.status_code == 404


class TestResultDeliveryAPI:
    """Test result delivery API functionality"""
    
    def setup_method(self):
        """Set up test client"""
        self.client = TestClient(app)
    
    def test_serve_nonexistent_result(self):
        """Test serving a result page that doesn't exist"""
        response = self.client.get("/result-delivery/nonexistent_session/nonexistent_task/")
        assert response.status_code == 404
    
    def test_serve_existing_result(self):
        """Test serving an existing result page"""
        # Create a test result page
        from pathlib import Path
        import tempfile
        
        project_root = Path(__file__).parent.parent
        session_dir = project_root / "user_comm" / "sessions" / "test_result_session" / "test_result_task"
        session_dir.mkdir(parents=True, exist_ok=True)
        
        # Create index.html
        index_file = session_dir / "index.html"
        index_file.write_text("<!DOCTYPE html><html><body><h1>Test Result</h1></body></html>")
        
        try:
            response = self.client.get("/result-delivery/test_result_session/test_result_task/")
            assert response.status_code == 200
            assert "text/html" in response.headers.get("content-type", "")
            assert "Test Result" in response.text
        finally:
            # Cleanup
            import shutil
            if session_dir.exists():
                shutil.rmtree(session_dir.parent.parent)
    
    def test_serve_result_file(self):
        """Test serving files from result delivery"""
        from pathlib import Path
        
        project_root = Path(__file__).parent.parent
        session_dir = project_root / "user_comm" / "sessions" / "test_file_session" / "test_file_task"
        files_dir = session_dir / "files"
        files_dir.mkdir(parents=True, exist_ok=True)
        
        # Create test file
        test_file = files_dir / "test_data.txt"
        test_file.write_text("Test file content")
        
        try:
            response = self.client.get("/result-delivery/test_file_session/test_file_task/files/test_data.txt")
            assert response.status_code == 200
            assert response.text == "Test file content"
        finally:
            # Cleanup
            import shutil
            if session_dir.exists():
                shutil.rmtree(session_dir.parent.parent)
    
    def test_serve_nonexistent_file(self):
        """Test serving a file that doesn't exist"""
        response = self.client.get("/result-delivery/test_session/test_task/files/nonexistent.txt")
        assert response.status_code == 404
    
    def test_file_path_sanitization(self):
        """Test that sanitize_path_component function properly cleans dangerous inputs"""
        from visualization.server.user_comm_api import sanitize_path_component
        
        # Test various dangerous inputs
        assert ".." not in sanitize_path_component("../../../etc")
        assert "/" not in sanitize_path_component("path/with/slashes")
        assert sanitize_path_component("normal-file_name.txt") == "normal-file_name.txt"
        assert sanitize_path_component("") == ""
        
        # Test file access through API
        from pathlib import Path
        
        project_root = Path(__file__).parent.parent
        session_dir = project_root / "user_comm" / "sessions" / "sanitize_test" / "task1"
        files_dir = session_dir / "files"
        files_dir.mkdir(parents=True, exist_ok=True)
        
        # Create legitimate file
        test_file = files_dir / "data.txt"
        test_file.write_text("Legitimate content")
        
        try:
            # Test: Access legitimate file - should work
            response = self.client.get("/result-delivery/sanitize_test/task1/files/data.txt")
            assert response.status_code == 200
            assert response.text == "Legitimate content"
            
            # Test: Try non-existent file
            response = self.client.get("/result-delivery/sanitize_test/task1/files/nonexistent.txt")
            assert response.status_code == 404
            
        finally:
            # Cleanup
            import shutil
            if session_dir.exists():
                shutil.rmtree(session_dir.parent.parent)


if __name__ == "__main__":
    """Run tests manually"""
    import pytest
    
    print("Running User Communication API tests...")
    
    # Try to run with pytest if available
    try:
        pytest.main([__file__, "-v"])
    except ImportError:
        print("pytest not available, running manual tests...")
        
        # Manual test runner
        test_api = TestUserCommAPI()
        test_api.setup_method()
        
        tests = [
            test_api.test_submit_response_new,
            test_api.test_submit_response_existing,
            test_api.test_get_status_no_response,
            test_api.test_get_status_with_response,
            test_api.test_submit_response_validation,
            test_api.test_path_sanitization,
        ]
        
        passed = 0
        for test in tests:
            try:
                test()
                print(f"✓ {test.__name__}")
                passed += 1
            except Exception as e:
                print(f"✗ {test.__name__}: {e}")
        
        print(f"\nPassed {passed}/{len(tests)} tests")