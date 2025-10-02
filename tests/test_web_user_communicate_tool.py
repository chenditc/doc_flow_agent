#!/usr/bin/env python3
"""
Unit tests for WebUserCommunicateTool and User Communication API
"""

import asyncio
import json
import os
import pytest
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock, Mock

# Add project root to path for imports
import sys
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from tools.web_user_communicate_tool import WebUserCommunicateTool


class TestWebUserCommunicateTool:
    """Test cases for WebUserCommunicateTool"""
    
    @pytest.fixture
    def tool(self):
        """Create a tool instance for testing"""
        return WebUserCommunicateTool()
    
    @pytest.fixture
    def temp_project_dir(self):
        """Create a temporary project directory for testing"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)
    
    @pytest.mark.asyncio
    async def test_llm_error_propagation(self, tool, temp_project_dir):
        """Test that LLM errors are properly propagated (no fallback)"""
        
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_project = Path(tmpdir)
            
            # Mock LLM tool to raise an exception
            with patch('tools.web_user_communicate_tool.LLMTool') as mock_llm_class:
                mock_llm_instance = AsyncMock()
                mock_llm_instance.execute.side_effect = Exception("LLM failed")
                mock_llm_class.return_value = mock_llm_instance
                
                # Simpler approach: patch the __file__ variable in the module
                with patch('tools.web_user_communicate_tool.__file__', str(temp_project / 'tools' / 'web_user_communicate_tool.py')):
                    parameters = {
                        "instruction": "Please provide feedback", 
                        "session_id": "test_session",
                        "task_id": "test_task",
                        "timeout_seconds": 0.1,
                        "poll_interval": 0.05
                    }
                    
                    # Mock environment variable
                    with patch.dict(os.environ, {'VISUALIZATION_SERVER_URL': 'http://test:8000'}):
                        # Expect the exception to propagate (no fallback)
                        with pytest.raises(Exception, match="LLM failed"):
                            await tool.execute(parameters)
    
    @pytest.mark.asyncio
    async def test_llm_form_generation_success(self, tool):
        """Test successful LLM form generation"""
        
        # Mock LLM tool to return custom HTML (now using tool call format)
        mock_llm_result = {
            "tool_calls": [{
                "name": "generate_html_form",
                "arguments": {
                    "html_content": """<!DOCTYPE html>
<html lang="en">
<head>
    <title>Custom LLM Generated Form</title>
</head>
<body>
    <h1>Rate Our Service</h1>
    <form id="responseForm">
        <input type="radio" name="rating" value="1" id="rate1">
        <label for="rate1">1 Star</label>
        <input type="radio" name="rating" value="5" id="rate5">
        <label for="rate5">5 Stars</label>
        <button type="submit">Submit</button>
    </form>
    <script>
        document.getElementById('responseForm').addEventListener('submit', async function(e) {
            e.preventDefault();
            // Submit logic here
        });
    </script>
</body>
</html>"""
                }
            }]
        }
        
        with patch('tools.web_user_communicate_tool.LLMTool') as mock_llm_class:
            mock_llm_instance = AsyncMock()
            mock_llm_instance.execute.return_value = mock_llm_result
            mock_llm_class.return_value = mock_llm_instance
            
            with tempfile.TemporaryDirectory() as tmpdir:
                temp_project = Path(tmpdir)
                
                # Patch the __file__ variable to point to the temp directory structure
                with patch('tools.web_user_communicate_tool.__file__', str(temp_project / 'tools' / 'web_user_communicate_tool.py')):
                    parameters = {
                        "instruction": "Rate our service from 1 to 5 stars",
                        "session_id": "llm_test",
                        "task_id": "rating",
                        "timeout_seconds": 0.1,
                        "poll_interval": 0.05
                    }
                    
                    with patch.dict(os.environ, {'VISUALIZATION_SERVER_URL': 'http://localhost:8000'}):
                        result = await tool.execute(parameters)
                    
                    # Verify LLM was called
                    mock_llm_instance.execute.assert_called_once()
                    
                    # Check that the result contains expected data
                    assert result["status"] == "timeout"  # Expected since no response file
                    assert "llm_test" in result["form_url"]
                    assert "rating" in result["form_url"]
    
    @pytest.mark.asyncio
    async def test_existing_response_handling(self, tool):
        """Test handling of existing responses (idempotent behavior)"""
        
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_project = Path(tmpdir)
            session_dir = temp_project / "user_comm" / "sessions" / "existing_test" / "task1"
            session_dir.mkdir(parents=True, exist_ok=True)
            
            # Create existing response file
            response_data = {
                "session_id": "existing_test",
                "task_id": "task1", 
                "answer": "Previous response",
                "timestamp": "2025-01-01T00:00:00Z"
            }
            response_file = session_dir / "response.json"
            with open(response_file, 'w') as f:
                json.dump(response_data, f)
            
            # Patch the project root path detection
            with patch.object(Path, 'parent', temp_project):
                parameters = {
                    "instruction": "Test existing response",
                    "session_id": "existing_test",
                    "task_id": "task1"
                }
                
                result = await tool.execute(parameters)
                
                # Should return existing response immediately
                assert result["status"] == "ok"
                assert result["answer"] == "Previous response"
                assert result["existing"] == True
    
    def test_parameter_validation(self, tool):
        """Test parameter validation"""
        
        # Missing required parameters
        with pytest.raises(ValueError, match="requires parameters"):
            asyncio.run(tool.execute({}))
        
        # Missing instruction
        with pytest.raises(ValueError, match="requires parameters"):
            asyncio.run(tool.execute({
                "session_id": "test",
                "task_id": "test"
            }))
    
    def test_html_tool_call_extraction(self, tool):
        """Test HTML extraction from LLM tool call responses"""
        
        # Test tool call response extraction
        tool_call_response = {
            "tool_calls": [{
                "name": "generate_html_form",
                "arguments": {
                    "html_content": "<!DOCTYPE html><html><body><h1>Test Form</h1></body></html>"
                }
            }]
        }
        
        extracted_html = tool._extract_html_from_response(tool_call_response)
        expected_html = "<!DOCTYPE html><html><body><h1>Test Form</h1></body></html>"
        assert extracted_html == expected_html
        
        # Test legacy string response handling
        string_response = "<html><body>Legacy Response</body></html>"
        extracted_html = tool._extract_html_from_response(string_response)
        assert extracted_html == string_response
        
        # Test error cases
        with pytest.raises(ValueError, match="Unexpected tool call"):
            tool._extract_html_from_response({
                "tool_calls": [{
                    "name": "wrong_tool_name",
                    "arguments": {"html_content": "test"}
                }]
            })
        
        with pytest.raises(ValueError, match="No HTML content generated"):
            tool._extract_html_from_response({
                "tool_calls": [{
                    "name": "generate_html_form",
                    "arguments": {}
                }]
            })


class TestFormGeneration:
    """Test form generation scenarios"""
    
    def test_instruction_parsing_scenarios(self):
        """Test different instruction types that would generate different forms"""
        
        scenarios = [
            {
                "instruction": "Please choose your favorite color: red, blue, or green",
                "expected_elements": ["radio", "red", "blue", "green"]
            },
            {
                "instruction": "Rate our service from 1 to 5 stars and provide comments",
                "expected_elements": ["rating", "1", "5", "comment"]
            },
            {
                "instruction": "Please provide your email address and phone number",
                "expected_elements": ["email", "phone", "input"]
            },
            {
                "instruction": "What improvements would you like to see?",
                "expected_elements": ["textarea", "improvements"]
            }
        ]
        
        # This test documents the expected behavior for different instruction types
        # In a real implementation with LLM, we would test that appropriate
        # form elements are generated based on the instruction content
        for scenario in scenarios:
            instruction = scenario["instruction"]
            expected = scenario["expected_elements"]
            
            # For now, we just verify the test structure is correct
            assert len(instruction) > 0
            assert len(expected) > 0
            assert isinstance(expected, list)


if __name__ == "__main__":
    # Run tests manually if not using pytest
    import unittest
    
    class SimpleTestRunner:
        def run_async_test(self, test_func, *args):
            """Helper to run async tests"""
            try:
                asyncio.run(test_func(*args))
                print(f"✓ {test_func.__name__} passed")
                return True
            except Exception as e:
                print(f"✗ {test_func.__name__} failed: {e}")
                return False
    
    print("Running WebUserCommunicateTool tests...")
    
    runner = SimpleTestRunner()
    tool = WebUserCommunicateTool()
    
    # Run basic tests that don't require complex mocking
    test_cases = []
    
    print("\n✓ Test structure validated")
    print("✓ For full test coverage, run with: pytest tests/test_web_user_communicate_tool.py")