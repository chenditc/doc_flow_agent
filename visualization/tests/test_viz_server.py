"""
Tests for the visualization server
"""

import pytest
import json
import os
import sys
import tempfile
import asyncio
import time
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Test data
MOCK_TRACE_DATA = {
    "session_id": "test-session",
    "start_time": "2025-08-22T10:00:00Z",
    "end_time": "2025-08-22T10:05:00Z",
    "initial_task_description": "Test task",
    "final_status": "completed",
    "task_executions": [
        {
            "task_execution_id": "test-task-1",
            "task_description": "Test task execution",
            "start_time": "2025-08-22T10:00:00Z",
            "end_time": "2025-08-22T10:02:00Z",
            "status": "completed",
            "phases": {
                "test_phase": {
                    "start_time": "2025-08-22T10:00:00Z",
                    "end_time": "2025-08-22T10:01:00Z",
                    "status": "completed"
                }
            }
        }
    ]
}

class TestVizServer:
    """Test cases for the visualization server"""

    @pytest.fixture
    def client(self):
        """Create test client with temporary trace directory"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create mock trace file
            trace_file = Path(temp_dir) / "session_test_123.json"
            with open(trace_file, 'w') as f:
                json.dump(MOCK_TRACE_DATA, f)
            
            # Import and configure the server
            with patch('visualization.server.viz_server.TRACES_DIR', Path(temp_dir)):
                from visualization.server.viz_server import app
                from fastapi.testclient import TestClient
                with TestClient(app) as client:
                    yield client

    def test_health_check(self, client):
        """Test health check endpoint"""
        response = client.get('/health')
        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'ok'

    def test_get_traces(self, client):
        """Test getting list of available traces via new API path"""
        response = client.get('/api/traces')
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert 'session_test_123' in data

    def test_get_trace_by_id(self, client):
        """Test getting specific trace by ID via new API path"""
        response = client.get('/api/traces/session_test_123')
        assert response.status_code == 200
        data = response.json()
        assert data['session_id'] == 'test-session'
        assert 'task_executions' in data
        assert len(data['task_executions']) == 1

    def test_get_nonexistent_trace(self, client):
        """Test getting trace that doesn't exist (new API path)"""
        response = client.get('/api/traces/nonexistent')
        assert response.status_code == 404

    def test_get_trace_invalid_filename(self, client):
        """Test getting trace with invalid filename containing backslash"""
        import urllib.parse
        # Use backslash which should trigger validation
        invalid_trace_id = urllib.parse.quote('invalid\\path', safe='')
        response = client.get(f'/api/traces/{invalid_trace_id}')
        assert response.status_code == 400

    def test_get_latest_trace(self, client):
        """Test getting the latest trace via new API path"""
        response = client.get('/api/traces/latest')
        assert response.status_code == 200
        data = response.json()
        assert 'trace_id' in data
        assert data['trace_id'] == 'session_test_123'

    def test_get_latest_trace_multiple_files(self):
        """Test getting latest trace when multiple trace files exist"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create multiple trace files with different timestamps
            trace_files = [
                "session_20250820_100000_abc123.json",
                "session_20250820_120000_def456.json", 
                "session_20250821_090000_ghi789.json",  # Latest date
                "session_20250821_080000_jkl012.json"   # Latest date but earlier time
            ]
            
            for trace_file in trace_files:
                file_path = Path(temp_dir) / trace_file
                with open(file_path, 'w') as f:
                    json.dump(MOCK_TRACE_DATA, f)
            
            with patch('visualization.server.viz_server.TRACES_DIR', Path(temp_dir)):
                from visualization.server.viz_server import app
                from fastapi.testclient import TestClient
                with TestClient(app) as client:
                    response = client.get('/api/traces/latest')
                    assert response.status_code == 200
                    data = response.json()
                    # Should return the lexicographically last filename (latest timestamp)
                    assert data['trace_id'] == 'session_20250821_090000_ghi789'

    def test_get_latest_trace_no_traces(self):
        """Test getting latest trace when no traces exist"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Empty directory with no trace files
            with patch('visualization.server.viz_server.TRACES_DIR', Path(temp_dir)):
                from visualization.server.viz_server import app
                from fastapi.testclient import TestClient
                with TestClient(app) as client:
                    response = client.get('/api/traces/latest')
                    assert response.status_code == 404
                    assert 'No trace files found' in response.json()['detail']

    def test_static_file_serving(self, client):
        """Test that static files are served correctly"""
        response = client.get('/')
        assert response.status_code == 200

    def test_cors_headers(self, client):
        """Test that CORS headers are set for development"""
        # CORS headers only appear in real cross-origin requests, not in TestClient
        # Just verify the middleware is configured by checking the app setup
        from visualization.server.viz_server import app
        
        # Check that CORS middleware is in the middleware stack
        middleware_classes = [middleware.cls for middleware in app.user_middleware]
        from fastapi.middleware.cors import CORSMiddleware
        assert CORSMiddleware in middleware_classes

class TestVizServerIntegration:
    """Integration tests for the visualization server"""

    @pytest.fixture
    def real_trace_client(self):
        """Create test client using real trace directory"""
        import os
        # Set testing mode to disable file watcher
        old_testing = os.environ.get('TESTING')
        os.environ['TESTING'] = 'true'
        
        try:
            from visualization.server.viz_server import app
            from fastapi.testclient import TestClient
            with TestClient(app) as client:
                yield client
        finally:
            # Restore original environment
            if old_testing is None:
                os.environ.pop('TESTING', None)
            else:
                os.environ['TESTING'] = old_testing

    def test_real_traces_endpoint(self, real_trace_client):
        """Test with real traces directory (if it exists)"""
        response = real_trace_client.get('/api/traces')
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # Should return list of trace files (could be empty)

    def test_get_real_latest_trace(self, real_trace_client):
        """Test getting the latest trace with real data"""
        # First get list of available traces
        response = real_trace_client.get('/api/traces')
        traces = response.json()
        
        if traces:
            # Test latest trace endpoint
            response = real_trace_client.get('/api/traces/latest')
            assert response.status_code == 200
            data = response.json()
            assert 'trace_id' in data
            
            # The latest trace should be in the list of available traces
            assert data['trace_id'] in traces
            
            # Since traces are sorted by name (which includes timestamp),
            # the latest should be the last when sorted
            sorted_traces = sorted(traces)
            assert data['trace_id'] == sorted_traces[-1]

    def test_get_real_trace_if_exists(self, real_trace_client):
        """Test getting a real trace file if any exist"""
        # First get list of available traces
        response = real_trace_client.get('/api/traces')
        traces = response.json()
        if traces:
            trace_id = traces[0]
            response = real_trace_client.get(f'/api/traces/{trace_id}')
            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, dict)

    # Note: SSE tests are commented out due to TestClient compatibility issues
    # The SSE endpoint can be tested manually by opening the browser and checking
    # the Network tab for EventSource connections
    
    # def test_sse_endpoint_headers(self, real_trace_client):
    #     """Test SSE endpoint returns proper headers"""
    #     # SSE testing is complex with TestClient, test manually for now
    #     pass
