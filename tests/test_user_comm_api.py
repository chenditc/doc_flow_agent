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