"""
Test configuration and utilities for visualization tests
"""

import os
import sys
from pathlib import Path

# Add the project root to Python path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Test constants
TEST_DATA_DIR = Path(__file__).parent / "test_data"
MOCK_TRACES_DIR = TEST_DATA_DIR / "traces"

# Create test data directories
TEST_DATA_DIR.mkdir(exist_ok=True)
MOCK_TRACES_DIR.mkdir(exist_ok=True)

# Environment configuration for tests
def setup_test_environment():
    """Set up test environment variables and configuration"""
    os.environ['TESTING'] = '1'
    os.environ['PYTHONPATH'] = str(project_root)

def teardown_test_environment():
    """Clean up test environment"""
    if 'TESTING' in os.environ:
        del os.environ['TESTING']

# Test data fixtures
SAMPLE_TASK_EXECUTION = {
    "task_execution_id": "test-task-1",
    "task_execution_counter": 0,
    "task_description": "Sample test task",
    "start_time": "2025-08-22T10:00:00Z",
    "end_time": "2025-08-22T10:02:00Z",
    "status": "completed",
    "error": None,
    "engine_state_before": {"context": {}},
    "engine_state_after": {
        "context": {
            "last_task_output": "Sample task output"
        }
    },
    "phases": {
        "sop_resolution": {
            "start_time": "2025-08-22T10:00:00Z",
            "end_time": "2025-08-22T10:01:00Z",
            "status": "completed",
            "input": {"description": "Sample test task"},
            "selected_doc_id": "test_doc"
        },
        "task_execution": {
            "start_time": "2025-08-22T10:01:00Z",
            "end_time": "2025-08-22T10:02:00Z", 
            "status": "completed",
            "tool_output": {"result": "success"}
        }
    }
}

SAMPLE_FAILED_TASK = {
    "task_execution_id": "test-task-failed",
    "task_execution_counter": 1,
    "task_description": "Sample failed task",
    "start_time": "2025-08-22T10:00:00Z",
    "end_time": "2025-08-22T10:01:00Z",
    "status": "failed",
    "error": "Sample error message",
    "engine_state_before": {"context": {}},
    "engine_state_after": {"context": {}},
    "phases": {
        "sop_resolution": {
            "start_time": "2025-08-22T10:00:00Z",
            "end_time": "2025-08-22T10:01:00Z",
            "status": "failed",
            "error": "Document not found"
        }
    }
}

SAMPLE_TRACE = {
    "session_id": "test-session-123",
    "start_time": "2025-08-22T10:00:00Z",
    "end_time": "2025-08-22T10:05:00Z",
    "initial_task_description": "Sample trace for testing",
    "final_status": "completed",
    "engine_snapshots": {
        "start": {
            "task_stack": [],
            "context": {},
            "task_execution_counter": 0
        }
    },
    "task_executions": [
        SAMPLE_TASK_EXECUTION,
        SAMPLE_FAILED_TASK
    ]
}
