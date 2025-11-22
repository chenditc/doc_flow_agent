#!/usr/bin/env python3
"""
Unit tests for WebResultDeliveryTool
"""

import asyncio
import json
import os
import pytest
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock

# Add project root to path for imports
import sys
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from tools.web_result_delivery_tool import WebResultDeliveryTool


def build_payload(
    session_id: str,
    task_id: str,
    *,
    blocks: list[dict] | None = None,
    assets: list[dict] | None = None,
    title: str = "Task Result",
    summary: str | None = None,
) -> dict:
    return {
        "version": "1.0",
        "meta": {
            "title": title,
            "session_id": session_id,
            "task_id": task_id,
        },
        "summary": summary,
        "blocks": blocks or [
            {
                "type": "text",
                "title": "Summary",
                "content": "Task completed",
                "format": "plain",
            }
        ],
        "assets": assets or [],
    }


class TestWebResultDeliveryTool:
    """Test cases for WebResultDeliveryTool"""
    
    @pytest.fixture
    def tool(self):
        """Create a tool instance for testing with mocked LLM"""
        mock_llm = AsyncMock()
        return WebResultDeliveryTool(llm_tool=mock_llm)
    
    @pytest.mark.asyncio
    async def test_basic_text_result_delivery(self, tool):
        """Test delivering a basic text result"""
        
        # Mock LLM tool to return HTML
        mock_llm_result = {
            "tool_calls": [{
                "name": "generate_html_result_page",
                "arguments": {
                    "html_content": """<!DOCTYPE html>
<html lang="en">
<head>
    <title>Task Result</title>
</head>
<body>
    <h1>Task Result</h1>
    <div>Test result content</div>
</body>
</html>""",
                    "file_mappings": []
                }
            }]
        }
        
        # Configure the tool's llm_tool mock
        tool.llm_tool.execute.return_value = mock_llm_result
        
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_project = Path(tmpdir)
            
            with patch('tools.web_result_delivery_tool.__file__', str(temp_project / 'tools' / 'web_result_delivery_tool.py')):
                with patch('utils.user_notify.notify_user'):
                    payload = build_payload(
                        "test_session",
                        "test_task",
                        blocks=[
                            {
                                "type": "text",
                                "title": "Status",
                                "content": "Task completed successfully",
                                "format": "plain",
                            }
                        ],
                    )
                    parameters = {
                        "result_data": payload,
                        "session_id": "test_session",
                        "task_id": "test_task"
                    }
                    
                    with patch.dict(os.environ, {'VISUALIZATION_SERVER_URL': 'http://localhost:8000'}):
                        result = await tool.execute(parameters)
                    
                    # Verify result
                    assert result["status"] == "ok"
                    assert result["result_url"] == "http://localhost:8000/result-delivery/test_session/test_task/"
                    assert result["pretty_result_url"] == "http://localhost:8000/result-delivery/test_session/test_task/pretty.html"
                    files_dir = temp_project / "user_comm" / "sessions" / "test_session" / "test_task" / "files"
                    data_file = files_dir / "result_data.json"
                    payload_file = files_dir / "delivery_payload.json"
                    assert result["file_included_in_html"] == sorted({str(data_file), str(payload_file)})
                    
                    # Verify LLM was called
                    tool.llm_tool.execute.assert_called_once()
                    
                    # Verify HTML file was created
                    session_dir = temp_project / "user_comm" / "sessions" / "test_session" / "test_task"
                    assert (session_dir / "index.html").exists()
                    assert (session_dir / "pretty.html").exists()
                    assert "Pretty format" in (session_dir / "index.html").read_text()
    
    @pytest.mark.asyncio
    async def test_result_with_files(self, tool):
        """Test delivering result with downloadable files"""
        
        # Create test files
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_project = Path(tmpdir)
            test_file1 = temp_project / "test1.txt"
            test_file1.write_text("Test file 1 content")
            test_file2 = temp_project / "test2.json"
            test_file2.write_text('{"key": "value"}')
            
            # Mock LLM to identify files in result_data and return file mappings
            mock_llm_result = {
                "tool_calls": [{
                    "name": "generate_html_result_page",
                    "arguments": {
                        "html_content": "<!DOCTYPE html><html><body><h1>Result with Files</h1></body></html>",
                        "file_mappings": [
                            {"source": str(test_file1), "target": "test1.txt", "type": "file"},
                            {"source": str(test_file2), "target": "test2.json", "type": "file"}
                        ]
                    }
                }]
            }
            
            # Configure the tool's llm_tool mock
            tool.llm_tool.execute.return_value = mock_llm_result
            
            with patch('tools.web_result_delivery_tool.__file__', str(temp_project / 'tools' / 'web_result_delivery_tool.py')):
                with patch('utils.user_notify.notify_user'):
                    payload = build_payload(
                        "file_test",
                        "task_files",
                        blocks=[
                            {
                                "type": "text",
                                "title": "Summary",
                                "content": "Results with files",
                                "format": "plain",
                            },
                            {"type": "file", "title": "File 1", "asset_id": "file_1"},
                            {"type": "file", "title": "File 2", "asset_id": "file_2"},
                        ],
                        assets=[
                            {
                                "id": "file_1",
                                "source_path": str(test_file1),
                                "filename": "test1.txt",
                                "asset_type": "file",
                            },
                            {
                                "id": "file_2",
                                "source_path": str(test_file2),
                                "filename": "test2.json",
                                "asset_type": "file",
                            },
                        ],
                    )
                    parameters = {
                        "result_data": payload,
                        "session_id": "file_test",
                        "task_id": "task_files"
                    }
                    
                    with patch.dict(os.environ, {'VISUALIZATION_SERVER_URL': 'http://localhost:8000'}):
                        result = await tool.execute(parameters)
                    
                    assert result["status"] == "ok"
                    assert result["pretty_result_url"] == "http://localhost:8000/result-delivery/file_test/task_files/pretty.html"
                    
                    # Verify files were copied
                    files_dir = temp_project / "user_comm" / "sessions" / "file_test" / "task_files" / "files"
                    assert (files_dir / "test1.txt").exists()
                    assert (files_dir / "test2.json").exists()
                    assert (files_dir / "test1.txt").read_text() == "Test file 1 content"
                    expected_files = {
                        str(files_dir / "result_data.json"),
                        str(files_dir / "delivery_payload.json"),
                        str(files_dir / "test1.txt"),
                        str(files_dir / "test2.json"),
                    }
                    assert set(result["file_included_in_html"]) == expected_files
    
    @pytest.mark.asyncio
    async def test_result_with_images(self, tool):
        """Test delivering result with image files"""
        
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_project = Path(tmpdir)
            test_image = temp_project / "chart.png"
            test_image.write_bytes(b"fake png data")
            
            # Mock LLM to identify image in result_data and return file mapping
            mock_llm_result = {
                "tool_calls": [{
                    "name": "generate_html_result_page",
                    "arguments": {
                        "html_content": "<!DOCTYPE html><html><body><img src='chart.png'/></body></html>",
                        "file_mappings": [
                            {"source": str(test_image), "target": "chart.png", "type": "image"}
                        ]
                    }
                }]
            }
            
            # Configure the tool's llm_tool mock
            tool.llm_tool.execute.return_value = mock_llm_result
            
            with patch('tools.web_result_delivery_tool.__file__', str(temp_project / 'tools' / 'web_result_delivery_tool.py')):
                with patch('utils.user_notify.notify_user'):
                    payload = build_payload(
                        "image_test",
                        "task_image",
                        blocks=[
                            {
                                "type": "text",
                                "title": "Summary",
                                "content": "Chart generated",
                                "format": "plain",
                            },
                            {
                                "type": "image",
                                "title": "Chart",
                                "asset_id": "img_1",
                                "alt_text": "Chart",
                            },
                        ],
                        assets=[
                            {
                                "id": "img_1",
                                "source_path": str(test_image),
                                "filename": "chart.png",
                                "asset_type": "image",
                            }
                        ],
                    )
                    parameters = {
                        "result_data": payload,
                        "session_id": "image_test",
                        "task_id": "task_image"
                    }
                    
                    with patch.dict(os.environ, {'VISUALIZATION_SERVER_URL': 'http://localhost:8000'}):
                        result = await tool.execute(parameters)
                    
                    assert result["status"] == "ok"
                    assert result["pretty_result_url"] == "http://localhost:8000/result-delivery/image_test/task_image/pretty.html"
                    
                    # Verify image was copied
                    files_dir = temp_project / "user_comm" / "sessions" / "image_test" / "task_image" / "files"
                    assert (files_dir / "chart.png").exists()
                    expected_files = {
                        str(files_dir / "result_data.json"),
                        str(files_dir / "delivery_payload.json"),
                        str(files_dir / "chart.png"),
                    }
                    assert set(result["file_included_in_html"]) == expected_files
    
    @pytest.mark.asyncio
    async def test_idempotent_delivery(self, tool):
        """Test that delivering result twice returns existing result"""
        
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_project = Path(tmpdir)
            session_dir = temp_project / "user_comm" / "sessions" / "existing_result" / "task1"
            session_dir.mkdir(parents=True, exist_ok=True)
            
            # Create existing index.html
            index_file = session_dir / "index.html"
            index_file.write_text("<!DOCTYPE html><html><body>Existing Result</body></html>")
            
            with patch('tools.web_result_delivery_tool.__file__', str(temp_project / 'tools' / 'web_result_delivery_tool.py')):
                parameters = {
                    "result_data": build_payload(
                        "existing_result",
                        "task1",
                        blocks=[
                            {
                                "type": "text",
                                "title": "Existing",
                                "content": "New result",
                                "format": "plain",
                            }
                        ],
                    ),
                    "session_id": "existing_result",
                    "task_id": "task1"
                }
                
                with patch.dict(os.environ, {'VISUALIZATION_SERVER_URL': 'http://localhost:8000'}):
                    result = await tool.execute(parameters)
                
                # Should return existing result
                assert result["status"] == "ok"
                assert result["file_included_in_html"] == []
                assert result["pretty_result_url"] == "http://localhost:8000/result-delivery/existing_result/task1/pretty.html"
                
                # HTML should not be modified
                assert index_file.read_text() == "<!DOCTYPE html><html><body>Existing Result</body></html>"

    @pytest.mark.asyncio
    async def test_sandbox_result_url(self, tool):
        """Ensure sandbox job IDs produce gateway URLs"""

        mock_llm_result = {
            "tool_calls": [{
                "name": "generate_html_result_page",
                "arguments": {
                    "html_content": "<!DOCTYPE html><html><body>Sandbox</body></html>",
                    "file_mappings": []
                }
            }]
        }
        tool.llm_tool.execute.return_value = mock_llm_result

        with tempfile.TemporaryDirectory() as tmpdir:
            temp_project = Path(tmpdir)
            with patch('tools.web_result_delivery_tool.__file__', str(temp_project / 'tools' / 'web_result_delivery_tool.py')):
                with patch('utils.user_notify.notify_user'):
                    parameters = {
                        "result_data": build_payload(
                            "sess123",
                            "task456",
                            blocks=[
                                {
                                    "type": "text",
                                    "title": "Sandbox",
                                    "content": "sandbox",
                                    "format": "plain",
                                }
                            ],
                        ),
                        "session_id": "sess123",
                        "task_id": "task456",
                        "job_id": "job789"
                    }
                    with patch.dict(os.environ, {'VISUALIZATION_SERVER_URL': 'http://localhost:8000'}):
                        result = await tool.execute(parameters)

                    expected = "http://localhost:8000/sandbox/job789/app/user_comm/sessions/sess123/task456/index.html"
                    assert result["result_url"] == expected
                    assert result["pretty_result_url"] == "http://localhost:8000/sandbox/job789/app/user_comm/sessions/sess123/task456/pretty.html"
                    files_dir = temp_project / "user_comm" / "sessions" / "sess123" / "task456" / "files"
                    assert result["file_included_in_html"] == sorted({
                        str(files_dir / "result_data.json"),
                        str(files_dir / "delivery_payload.json"),
                    })
    
    @pytest.mark.asyncio
    async def test_json_result_data(self, tool):
        """Test delivering JSON result data"""
        
        mock_llm_result = {
            "tool_calls": [{
                "name": "generate_html_result_page",
                "arguments": {
                    "html_content": "<!DOCTYPE html><html><body><pre>JSON</pre></body></html>",
                    "file_mappings": []
                }
            }]
        }
        
        # Configure the tool's llm_tool mock
        tool.llm_tool.execute.return_value = mock_llm_result
        
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_project = Path(tmpdir)
            
            with patch('tools.web_result_delivery_tool.__file__', str(temp_project / 'tools' / 'web_result_delivery_tool.py')):
                with patch('utils.user_notify.notify_user'):
                    raw_content = json.dumps({"status": "success", "count": 42, "items": ["a", "b", "c"]})
                    payload = build_payload(
                        "json_test",
                        "task_json",
                        blocks=[
                            {
                                "type": "json",
                                "title": "Raw Data",
                                "content": raw_content,
                                "format": "json",
                            }
                        ],
                    )
                    parameters = {
                        "result_data": payload,
                        "session_id": "json_test",
                        "task_id": "task_json"
                    }
                    
                    with patch.dict(os.environ, {'VISUALIZATION_SERVER_URL': 'http://localhost:8000'}):
                        result = await tool.execute(parameters)
                    
                    assert result["status"] == "ok"
                    
                    # Verify LLM received JSON string
                    call_args = tool.llm_tool.execute.call_args
                    prompt = call_args[0][0]["prompt"]
                    assert '"Raw Data"' in prompt
                    assert "status" in prompt
    
    @pytest.mark.asyncio
    async def test_llm_error_propagation(self, tool):
        """Test that LLM errors are properly propagated"""
        
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_project = Path(tmpdir)
            
            # Configure the tool's llm_tool mock to raise an exception
            tool.llm_tool.execute.side_effect = Exception("LLM failed")
            
            with patch('tools.web_result_delivery_tool.__file__', str(temp_project / 'tools' / 'web_result_delivery_tool.py')):
                with patch('utils.user_notify.notify_user'):
                    parameters = {
                        "result_data": build_payload(
                            "error_test",
                            "task_error",
                            blocks=[
                                {
                                    "type": "text",
                                    "title": "Error",
                                    "content": "Test data",
                                    "format": "plain",
                                }
                            ],
                        ),
                        "session_id": "error_test",
                        "task_id": "task_error"
                    }
                    
                    with patch.dict(os.environ, {'VISUALIZATION_SERVER_URL': 'http://localhost:8000'}):
                        # Expect the exception to propagate
                        with pytest.raises(Exception, match="LLM failed"):
                            await tool.execute(parameters)
    
    def test_parameter_validation(self, tool):
        """Test parameter validation"""
        
        # Missing required parameters
        with pytest.raises(ValueError, match="requires parameters"):
            asyncio.run(tool.execute({}))
        
        # Missing result_data
        with pytest.raises(ValueError, match="requires parameters"):
            asyncio.run(tool.execute({
                "session_id": "test",
                "task_id": "test"
            }))
    
    def test_html_extraction(self, tool):
        """Test HTML extraction from LLM responses"""
        
        # Test tool call response with file mappings
        tool_call_response = {
            "tool_calls": [{
                "name": "generate_html_result_page",
                "arguments": {
                    "html_content": "<!DOCTYPE html><html><body>Result</body></html>",
                    "file_mappings": [{"source": "/path/to/file.txt", "target": "file.txt", "type": "file"}]
                }
            }]
        }
        
        html_content, file_mappings = tool._extract_html_from_response(tool_call_response)
        assert html_content == "<!DOCTYPE html><html><body>Result</body></html>"
        assert len(file_mappings) == 1
        assert file_mappings[0]["source"] == "/path/to/file.txt"
        
        # Legacy string responses are no longer supported
        string_response = "<html><body>Legacy</body></html>"
        with pytest.raises(ValueError, match="No tool calls found"):
            tool._extract_html_from_response(string_response)
    
    @pytest.mark.asyncio
    async def test_missing_file_handling(self, tool):
        """Test that missing files are skipped gracefully"""
        
        # Mock LLM to return file mappings with non-existent files
        mock_llm_result = {
            "tool_calls": [{
                "name": "generate_html_result_page",
                "arguments": {
                    "html_content": "<!DOCTYPE html><html><body>Result</body></html>",
                    "file_mappings": [
                        {"source": "/nonexistent/file.txt", "target": "file.txt", "type": "file"},
                        {"source": "", "target": "empty.txt", "type": "file"}
                    ]
                }
            }]
        }
        
        # Configure the tool's llm_tool mock
        tool.llm_tool.execute.return_value = mock_llm_result
        
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_project = Path(tmpdir)
            
            with patch('tools.web_result_delivery_tool.__file__', str(temp_project / 'tools' / 'web_result_delivery_tool.py')):
                with patch('utils.user_notify.notify_user'):
                    payload = build_payload(
                        "missing_file_test",
                        "task_missing",
                        blocks=[
                            {"type": "text", "title": "Result", "content": "Result", "format": "plain"},
                            {"type": "file", "title": "Missing", "asset_id": "file_1"},
                        ],
                        assets=[
                            {
                                "id": "file_1",
                                "source_path": "/nonexistent/file.txt",
                                "filename": "file.txt",
                                "asset_type": "file",
                            }
                        ],
                    )
                    parameters = {
                        "result_data": payload,
                        "session_id": "missing_file_test",
                        "task_id": "task_missing"
                    }
                    
                    with patch.dict(os.environ, {'VISUALIZATION_SERVER_URL': 'http://localhost:8000'}):
                        with pytest.raises(ValueError, match="Failed to normalize result data"):
                            await tool.execute(parameters)

    @pytest.mark.asyncio
    async def test_retry_on_value_error(self, tool):
        """Test that ValueError during HTML parsing triggers retries"""

        responses = [
            {"tool_calls": []},  # Will cause ValueError: No tool calls
            {
                "tool_calls": [{
                    "name": "generate_html_result_page",
                    "arguments": {
                        "html_content": "<!DOCTYPE html><html><body>Valid</body></html>",
                        "file_mappings": []
                    }
                }]
            }
        ]

        async def mock_execute(params, **kwargs):
            validators = kwargs.get("validators") or []
            max_attempts = kwargs.get("max_retries", 0) + 1
            attempt_counter = 0
            while True:
                if not responses:
                    raise ValueError("LLM failed to produce valid HTML content after retries")
                payload = responses.pop(0)
                attempt_counter += 1
                try:
                    for validator in validators:
                        validator(payload)
                except ValueError as exc:
                    if attempt_counter >= max_attempts:
                        raise ValueError(f"LLM failed to produce valid HTML content after {max_attempts} attempts") from exc
                    continue
                return payload

        tool.llm_tool.execute.side_effect = mock_execute

        with tempfile.TemporaryDirectory() as tmpdir:
            temp_project = Path(tmpdir)

            with patch('tools.web_result_delivery_tool.__file__', str(temp_project / 'tools' / 'web_result_delivery_tool.py')):
                with patch('utils.user_notify.notify_user'):
                    parameters = {
                        "result_data": build_payload(
                            "retry_session",
                            "retry_task",
                            blocks=[
                                {
                                    "type": "text",
                                    "title": "Retry",
                                    "content": "Retry test",
                                    "format": "plain",
                                }
                            ],
                        ),
                        "session_id": "retry_session",
                        "task_id": "retry_task"
                    }

                    with patch.dict(os.environ, {'VISUALIZATION_SERVER_URL': 'http://localhost:8000'}):
                        result = await tool.execute(parameters)

                    assert result["status"] == "ok"

    @pytest.mark.asyncio
    async def test_retry_exhaustion_raises_value_error(self):
        """Test that ValueError is raised after exhausting retries"""

        mock_llm = AsyncMock()
        tool = WebResultDeliveryTool(llm_tool=mock_llm, max_generation_attempts=2)

        responses = [{"tool_calls": []}, {"tool_calls": []}]

        async def mock_execute(params, **kwargs):
            validators = kwargs.get("validators") or []
            max_attempts = kwargs.get("max_retries", 0) + 1
            attempt_counter = 0
            while True:
                if not responses:
                    raise ValueError("LLM failed to produce valid HTML content after retries")
                payload = responses.pop(0)
                attempt_counter += 1
                try:
                    for validator in validators:
                        validator(payload)
                except ValueError as exc:
                    if attempt_counter >= max_attempts:
                        raise ValueError(f"LLM failed to produce valid HTML content after {max_attempts} attempts") from exc
                    continue
                return payload

        tool.llm_tool.execute.side_effect = mock_execute

        with tempfile.TemporaryDirectory() as tmpdir:
            temp_project = Path(tmpdir)

            with patch('tools.web_result_delivery_tool.__file__', str(temp_project / 'tools' / 'web_result_delivery_tool.py')):
                with patch('utils.user_notify.notify_user'):
                    parameters = {
                        "result_data": build_payload(
                            "retry_fail_session",
                            "retry_fail_task",
                            blocks=[
                                {
                                    "type": "text",
                                    "title": "Retry",
                                    "content": "Failure test",
                                    "format": "plain",
                                }
                            ],
                        ),
                        "session_id": "retry_fail_session",
                        "task_id": "retry_fail_task"
                    }

                    with patch.dict(os.environ, {'VISUALIZATION_SERVER_URL': 'http://localhost:8000'}):
                        with pytest.raises(ValueError, match="LLM failed to produce valid HTML content after 2 attempts"):
                            await tool.execute(parameters)



if __name__ == "__main__":
    """Run tests manually"""
    pytest.main([__file__, "-v"])
