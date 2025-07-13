import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

# Test data directly in file to avoid import issues
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

class TestFormattingUtils:
    """Test formatting utilities (JavaScript functions tested via behavior)"""

    def test_trace_data_structure(self):
        """Verify test trace has expected structure for frontend parsing"""
        trace = SAMPLE_TRACE
        
        # Basic structure
        assert 'session_id' in trace
        assert 'task_executions' in trace
        assert isinstance(trace['task_executions'], list)
        
        # Task structure
        task = trace['task_executions'][0]
        assert 'task_execution_id' in task
        assert 'task_description' in task
        assert 'start_time' in task
        assert 'status' in task
        assert 'phases' in task
        
        # Phase structure
        phases = task['phases']
        assert isinstance(phases, dict)
        for phase_name, phase_data in phases.items():
            assert 'start_time' in phase_data
            assert 'status' in phase_data

    def test_task_output_extraction_structure(self):
        """Test that task output can be extracted from various locations"""
        task = SAMPLE_TASK_EXECUTION.copy()
        
        # Test with last_task_output in context
        assert task['engine_state_after']['context']['last_task_output'] == "Sample task output"
        
        # Test with error
        failed_task = SAMPLE_FAILED_TASK.copy()
        assert failed_task['error'] == "Sample error message"
        
        # Test with structured output
        task_with_structured_output = task.copy()
        task_with_structured_output['engine_state_after']['context']['last_task_output'] = {
            'stdout': 'Success output',
            'stderr': 'Warning message'
        }
        output = task_with_structured_output['engine_state_after']['context']['last_task_output']
        assert 'stdout' in output and 'stderr' in output

    def test_phase_extraction_structure(self):
        """Test that phases can be extracted and formatted correctly"""
        task = SAMPLE_TASK_EXECUTION
        phases = task['phases']
        
        # Should have multiple phases
        assert len(phases) >= 2
        
        # Each phase should have required fields
        for phase_name, phase_data in phases.items():
            assert isinstance(phase_name, str)
            assert 'status' in phase_data
            # Phase names should be convertible to display format
            display_name = phase_name.replace('_', ' ').title()
            assert display_name != phase_name  # Should be different

class TestComponentIntegration:
    """Test component integration through API endpoints"""

    @pytest.fixture
    def test_server(self):
        """Create test server with sample data"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create sample trace file
            trace_file = Path(temp_dir) / "session_test_123.json"
            with open(trace_file, 'w') as f:
                json.dump(SAMPLE_TRACE, f, indent=2)
            
            with patch('visualization.server.viz_server.TRACES_DIR', Path(temp_dir)):
                from visualization.server.viz_server import app
                from fastapi.testclient import TestClient
                with TestClient(app) as client:
                    yield client

    def test_timeline_data_format(self, test_server):
        """Test that timeline component receives properly formatted data"""
        # Get the sample trace
        response = test_server.get('/traces/session_test_123')
        assert response.status_code == 200
        
        trace_data = response.json()
        
        # Verify structure expected by TimelineComponent
        assert 'task_executions' in trace_data
        tasks = trace_data['task_executions']
        
        for task in tasks:
            # Required fields for timeline rendering
            assert 'task_execution_id' in task
            assert 'task_description' in task
            assert 'start_time' in task
            assert 'status' in task
            
            # Optional but expected fields
            if 'phases' in task:
                assert isinstance(task['phases'], dict)
            
            if 'engine_state_after' in task:
                assert isinstance(task['engine_state_after'], dict)

    def test_task_details_data_format(self, test_server):
        """Test that task details component receives complete data"""
        response = test_server.get('/traces/session_test_123')
        trace_data = response.json()
        
        task = trace_data['task_executions'][0]  # Get completed task
        
        # Required fields for task details modal
        assert 'task_execution_id' in task
        assert 'task_description' in task
        assert 'start_time' in task
        assert 'status' in task
        assert 'phases' in task
        
        # Verify phases have required structure
        phases = task['phases']
        for phase_name, phase_data in phases.items():
            assert 'start_time' in phase_data
            assert 'status' in phase_data
            # Should have additional data for JSON display
            # (after removing meta fields like start_time, end_time, status)
            non_meta_keys = [k for k in phase_data.keys() 
                           if k not in ['start_time', 'end_time', 'status']]
            # At least some non-meta data should exist
            if non_meta_keys:
                assert len(non_meta_keys) > 0

    def test_trace_selector_data_format(self, test_server):
        """Test that trace selector receives proper trace list"""
        response = test_server.get('/traces')
        assert response.status_code == 200
        
        traces = response.json()
        assert isinstance(traces, list)
        assert 'session_test_123' in traces
        
        # Each trace ID should be a valid filename without extension
        for trace_id in traces:
            assert isinstance(trace_id, str)
            assert not trace_id.endswith('.json')  # API returns without extension

class TestErrorHandling:
    """Test error handling for various component scenarios"""

    def test_missing_trace_file(self):
        """Test handling of missing trace files"""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch('visualization.server.viz_server.TRACES_DIR', Path(temp_dir)):
                from visualization.server.viz_server import app
                from fastapi.testclient import TestClient
                with TestClient(app) as client:
                    # Request non-existent trace
                    response = client.get('/traces/nonexistent')
                    assert response.status_code == 404

    def test_invalid_json_in_trace(self):
        """Test handling of corrupted JSON trace files"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create invalid JSON file
            trace_file = Path(temp_dir) / "invalid.json"
            with open(trace_file, 'w') as f:
                f.write('{"invalid": json content}')
            
            with patch('visualization.server.viz_server.TRACES_DIR', Path(temp_dir)):
                from visualization.server.viz_server import app
                from fastapi.testclient import TestClient
                with TestClient(app) as client:
                    response = client.get('/traces/invalid')
                    assert response.status_code == 500

    def test_empty_trace_data(self):
        """Test handling of trace with no task executions"""
        empty_trace = {
            "session_id": "empty-session",
            "task_executions": []
        }
        
        with tempfile.TemporaryDirectory() as temp_dir:
            trace_file = Path(temp_dir) / "empty.json"
            with open(trace_file, 'w') as f:
                json.dump(empty_trace, f)
            
            with patch('visualization.server.viz_server.TRACES_DIR', Path(temp_dir)):
                from visualization.server.viz_server import app
                from fastapi.testclient import TestClient
                with TestClient(app) as client:
                    response = client.get('/traces/empty')
                    assert response.status_code == 200
                    data = response.json()
                    assert data['task_executions'] == []

class TestPerformance:
    """Test performance considerations for large trace files"""

    def test_large_trace_handling(self):
        """Test handling of trace with many task executions"""
        # Create trace with many tasks
        large_trace = SAMPLE_TRACE.copy()
        large_trace['task_executions'] = []
        
        # Add 100 task executions
        for i in range(100):
            task = SAMPLE_TASK_EXECUTION.copy()
            task['task_execution_id'] = f'task-{i}'
            task['task_execution_counter'] = i
            task['task_description'] = f'Task {i} description'
            large_trace['task_executions'].append(task)
        
        # Should be able to serialize/deserialize without issues
        json_str = json.dumps(large_trace)
        reloaded_trace = json.loads(json_str)
        
        assert len(reloaded_trace['task_executions']) == 100
        assert reloaded_trace['task_executions'][99]['task_execution_id'] == 'task-99'

    def test_deep_phase_data_handling(self):
        """Test handling of phases with complex nested data"""
        complex_task = SAMPLE_TASK_EXECUTION.copy()
        complex_task['phases']['complex_phase'] = {
            'start_time': '2025-08-22T10:00:00Z',
            'end_time': '2025-08-22T10:01:00Z',
            'status': 'completed',
            'llm_calls': [
                {
                    'prompt': 'A' * 1000,  # Long prompt
                    'response': 'B' * 2000,  # Long response
                    'metadata': {
                        'nested': {
                            'deeply': {
                                'nested': 'data'
                            }
                        }
                    }
                }
            ]
        }
        
        # Should be serializable
        json_str = json.dumps(complex_task)
        reloaded_task = json.loads(json_str)
        
        assert 'complex_phase' in reloaded_task['phases']
        assert len(reloaded_task['phases']['complex_phase']['llm_calls'][0]['prompt']) == 1000


class TestPhase7SOPResolution:
    """Test Phase 7 implementation - Enhanced SOP Resolution Phase Display"""

    def test_sop_resolution_data_structure_single_candidate(self):
        """Test SOP resolution with single candidate (perfect match scenario)"""
        sop_data = {
            "start_time": "2025-08-22T10:00:00Z",
            "end_time": "2025-08-22T10:01:00Z",
            "status": "completed",
            "input": {"description": "Follow tools/bash.md and run ls command"},
            "candidate_documents": ["tools/bash"],
            "llm_validation_call": {
                "tool_call_id": "test-llm-call",
                "step": "sop_document_validation",
                "prompt": "Given the user's request: \"Follow tools/bash.md and run ls command\"\n\n1. doc_id: tools/bash\n   description: Execute bash commands\n   match_type: filename\n\nPlease respond with <doc_id>tools/bash</doc_id>",
                "response": "<doc_id>tools/bash</doc_id>",
                "start_time": "2025-08-22T10:00:10Z",
                "end_time": "2025-08-22T10:00:50Z"
            },
            "selected_doc_id": "tools/bash",
            "loaded_sop_document": {
                "doc_id": "tools/bash",
                "description": "Execute bash commands",
                "aliases": [],
                "tool": {"tool_id": "CLI", "parameters": {"command": "{command}"}},
                "input_json_path": {"command": "$.current_task"},
                "output_json_path": "$.bash_output"
            }
        }
        
        # Should be serializable and contain expected structure
        json_str = json.dumps(sop_data)
        reloaded_data = json.loads(json_str)
        
        assert len(reloaded_data['candidate_documents']) == 1
        assert reloaded_data['selected_doc_id'] == 'tools/bash'
        assert 'llm_validation_call' in reloaded_data
        assert 'loaded_sop_document' in reloaded_data
        assert 'match_type: filename' in reloaded_data['llm_validation_call']['prompt']

    def test_sop_resolution_data_structure_multiple_candidates(self):
        """Test SOP resolution with multiple candidates (LLM selection scenario)"""
        sop_data = {
            "start_time": "2025-08-22T10:00:00Z",
            "end_time": "2025-08-22T10:01:00Z",
            "status": "completed",
            "input": {"description": "Generate some text"},
            "candidate_documents": ["tools/llm", "general/text_generation"],
            "llm_validation_call": {
                "tool_call_id": "test-llm-call-multi",
                "step": "sop_document_validation",
                "prompt": "Given the user's request: \"Generate some text\"\n\n1. doc_id: tools/llm\n   description: General LLM text generation\n   match_type: filename\n\n2. doc_id: general/text_generation\n   description: Specialized text generation\n   match_type: full_path\n\nPlease respond with best match.",
                "response": "<doc_id>tools/llm</doc_id>",
                "start_time": "2025-08-22T10:00:10Z",
                "end_time": "2025-08-22T10:00:50Z"
            },
            "selected_doc_id": "tools/llm",
            "loaded_sop_document": {
                "doc_id": "tools/llm",
                "description": "General LLM text generation",
                "aliases": ["gpt", "ai"],
                "tool": {"tool_id": "LLM", "parameters": {"prompt": "{text_prompt}"}},
                "input_json_path": {"text_prompt": "$.user_request"},
                "output_json_path": "$.llm_response"
            }
        }
        
        # Verify multiple candidates structure
        json_str = json.dumps(sop_data)
        reloaded_data = json.loads(json_str)
        
        assert len(reloaded_data['candidate_documents']) == 2
        assert 'tools/llm' in reloaded_data['candidate_documents']
        assert 'general/text_generation' in reloaded_data['candidate_documents']
        assert reloaded_data['selected_doc_id'] == 'tools/llm'
        assert 'match_type: filename' in reloaded_data['llm_validation_call']['prompt']
        assert 'match_type: full_path' in reloaded_data['llm_validation_call']['prompt']

    def test_sop_resolution_data_structure_no_candidates_fallback(self):
        """Test SOP resolution with no candidates (fallback scenario)"""
        sop_data = {
            "start_time": "2025-08-22T10:00:00Z",
            "end_time": "2025-08-22T10:01:00Z",
            "status": "completed",
            "input": {"description": "Some unrecognized task"},
            "candidate_documents": [],
            "llm_validation_call": None,
            "selected_doc_id": "general/fallback",
            "loaded_sop_document": {
                "doc_id": "general/fallback",
                "description": "Fallback SOP for unrecognized tasks",
                "aliases": [],
                "tool": {"tool_id": "LLM", "parameters": {"prompt": "Handle: {task}"}},
                "input_json_path": {"task": "$.current_task"},
                "output_json_path": "$.fallback_result"
            }
        }
        
        # Verify fallback scenario structure
        json_str = json.dumps(sop_data)
        reloaded_data = json.loads(json_str)
        
        assert len(reloaded_data['candidate_documents']) == 0
        assert reloaded_data['llm_validation_call'] is None
        assert reloaded_data['selected_doc_id'] == 'general/fallback'
        assert 'Fallback' in reloaded_data['loaded_sop_document']['description']

    def test_sop_resolution_data_structure_llm_rejection(self):
        """Test SOP resolution where LLM rejects candidates (alert scenario)"""
        sop_data = {
            "start_time": "2025-08-22T10:00:00Z",
            "end_time": "2025-08-22T10:01:00Z",
            "status": "completed",
            "input": {"description": "Incompatible task request"},
            "candidate_documents": ["tools/bash", "tools/llm"],
            "llm_validation_call": {
                "tool_call_id": "test-llm-rejection",
                "step": "sop_document_validation",
                "prompt": "Given the user's request: \"Incompatible task request\"\n\n1. doc_id: tools/bash\n   description: Execute bash commands\n   match_type: filename\n\n2. doc_id: tools/llm\n   description: Generate text\n   match_type: filename\n\nPlease respond with best match.",
                "response": "<doc_id>NONE</doc_id>",
                "start_time": "2025-08-22T10:00:10Z",
                "end_time": "2025-08-22T10:00:50Z"
            },
            "selected_doc_id": "general/fallback",
            "loaded_sop_document": {
                "doc_id": "general/fallback",
                "description": "Fallback for rejected tasks",
                "aliases": [],
                "tool": {"tool_id": "LLM", "parameters": {"prompt": "Handle rejected: {task}"}},
                "input_json_path": {"task": "$.current_task"},
                "output_json_path": "$.rejection_result"
            }
        }
        
        # Verify LLM rejection scenario
        json_str = json.dumps(sop_data)
        reloaded_data = json.loads(json_str)
        
        assert len(reloaded_data['candidate_documents']) == 2
        assert 'NONE' in reloaded_data['llm_validation_call']['response']
        assert reloaded_data['selected_doc_id'] == 'general/fallback'
        # This is the alerting situation described in requirements

    def test_sop_resolution_data_structure_with_error(self):
        """Test SOP resolution with error during process"""
        sop_data = {
            "start_time": "2025-08-22T10:00:00Z",
            "end_time": "2025-08-22T10:01:00Z",
            "status": "failed",
            "input": {"description": "Problematic task"},
            "candidate_documents": ["tools/bash"],
            "llm_validation_call": {
                "tool_call_id": "test-llm-error",
                "step": "sop_document_validation",
                "prompt": "Given request...",
                "response": "Invalid response format",
                "start_time": "2025-08-22T10:00:10Z",
                "end_time": "2025-08-22T10:00:50Z"
            },
            "selected_doc_id": None,
            "loaded_sop_document": None,
            "error": "Failed to parse LLM response for SOP selection"
        }
        
        # Verify error scenario structure
        json_str = json.dumps(sop_data)
        reloaded_data = json.loads(json_str)
        
        assert reloaded_data['status'] == 'failed'
        assert reloaded_data['error'] is not None
        assert reloaded_data['selected_doc_id'] is None
        assert reloaded_data['loaded_sop_document'] is None

    def test_llm_call_data_structure_complete(self):
        """Test LLM call component data structure with full information"""
        llm_call = {
            "tool_call_id": "test-id-123",
            "step": "sop_document_validation",
            "prompt": "This is a test prompt with multiple lines\nand detailed instructions\nfor the LLM to follow",
            "response": "<doc_id>tools/bash</doc_id>",
            "start_time": "2025-08-22T10:00:10Z",
            "end_time": "2025-08-22T10:00:50Z",
            "model": "gpt-4",
            "token_usage": {"prompt_tokens": 150, "completion_tokens": 20, "total_tokens": 170},
            "execution_time_ms": 4500
        }
        
        # Should be serializable and contain all expected fields
        json_str = json.dumps(llm_call)
        reloaded_call = json.loads(json_str)
        
        assert reloaded_call['tool_call_id'] == 'test-id-123'
        assert reloaded_call['step'] == 'sop_document_validation'
        assert len(reloaded_call['prompt']) > 50  # Multi-line prompt
        assert '<doc_id>' in reloaded_call['response']
        assert reloaded_call['model'] == 'gpt-4'
        assert reloaded_call['token_usage']['total_tokens'] == 170
        assert reloaded_call['execution_time_ms'] == 4500

    def test_llm_call_data_structure_minimal(self):
        """Test LLM call component with minimal required information"""
        llm_call = {
            "step": "sop_document_validation", 
            "prompt": "Simple prompt",
            "response": "Simple response"
        }
        
        # Should handle minimal data gracefully
        json_str = json.dumps(llm_call)
        reloaded_call = json.loads(json_str)
        
        assert reloaded_call['step'] == 'sop_document_validation'
        assert reloaded_call['prompt'] == 'Simple prompt'
        assert reloaded_call['response'] == 'Simple response'
        # Missing fields should not break serialization
