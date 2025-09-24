#!/usr/bin/env python3
"""
Example Integration Test using the Save/Mock Framework
Demonstrates testing DocExecuteEngine with tool recording/playback
"""

import asyncio
import sys
import os
import pytest
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from integration_test_framework import IntegrationTestBase, IntegrationTestMode, get_test_mode, print_test_mode_info
from tools.llm_tool import LLMTool
from tools.cli_tool import CLITool
from tools.user_communicate_tool import UserCommunicateTool
from tools.python_executor_tool import PythonExecutorTool
from doc_execute_engine import DocExecuteEngine
from sop_document import SOPDocumentParser


class TestDocExecuteEngineIntegration:
    """Integration test for DocExecuteEngine with save/mock capabilities"""
    
    def setup_method(self, method):
        """Set up test fixtures"""
        self.test_mode = get_test_mode()
        print_test_mode_info(self.test_mode)
        
        # Use method name to create unique test names
        test_name = f"doc_execute_engine_{method.__name__}"
        
        # Initialize integration test framework
        self.integration_test = IntegrationTestBase(
            test_name=test_name,
            mode=self.test_mode
        )
        
        # Create wrapped tools
        self.llm_tool = self.integration_test.wrap_tool(LLMTool())
        self.cli_tool = self.integration_test.wrap_tool(CLITool(llm_tool=self.llm_tool))
        self.user_tool = self.integration_test.wrap_tool(UserCommunicateTool())
        self.python_tool = self.integration_test.wrap_tool(PythonExecutorTool(llm_tool=self.llm_tool))
        
        # Create DocExecuteEngine with wrapped tools
        self.engine = DocExecuteEngine()
        
        # Replace the engine's tools with our wrapped versions
        self.engine.tools = {
            "LLM": self.llm_tool,
            "CLI": self.cli_tool,
            "USER_COMMUNICATE": self.user_tool,
            "PYTHON_EXECUTOR": self.python_tool
        }
        
        # Recreate JsonPathGenerator with the wrapped LLM tool
        from tools.json_path_generator import SmartJsonPathGenerator
        self.engine.json_path_generator = SmartJsonPathGenerator(self.llm_tool)

        # Inject SOP document parser
        self.engine.sop_parser = SOPDocumentParser(llm_tool=self.llm_tool, tracer=self.engine.tracer)
    
    def teardown_method(self):
        """Clean up and save test data if in real mode"""
        if self.test_mode == IntegrationTestMode.REAL or self.test_mode == IntegrationTestMode.MOCK_THEN_REAL:
            self.integration_test.save_test_data()
    
    @pytest.mark.asyncio
    async def test_basic_document_execution(self):
        """Test basic document execution flow"""
        # Sample input data - just a simple task description
        initial_task = "Write a simple Python script that prints 'Hello World'"
        
        # Execute the task using start method (this is the main entry point)
        result = await self.engine.start(initial_task)
        
        # The start method doesn't return a specific result, but we can check
        # that the engine executed without errors and has some context
        assert self.engine.context is not None
        
        print(f"✅ Execution completed successfully")
        print(f"   Context keys: {list(self.engine.context.keys())}")

    
    @pytest.mark.asyncio
    async def test_llm_tool_direct(self):
        """Test LLM tool directly with save/mock"""
        prompt = "Generate a simple Python function that adds two numbers"
        
        try:
            result = await self.llm_tool.execute({
                "prompt": prompt
            })
            
            # Verify response structure
            assert result is not None
            assert isinstance(result, dict), f"Expected dict response, got {type(result)}"
            assert "content" in result, f"Expected 'content' key in response: {result}"
            assert "tool_calls" in result, f"Expected 'tool_calls' key in response: {result}"
            
            if self.test_mode == IntegrationTestMode.REAL:
                # In real mode, we expect actual LLM response
                assert "def" in result["content"].lower()  # Should contain function definition
            
            print(f"✅ LLM tool test completed")
            print(f"   Response length: {len(str(result['content']))}")
            if result["tool_calls"]:
                print(f"   Tool calls: {len(result['tool_calls'])}")
            
        except RuntimeError as e:
            if "Failed to connect to LLM API" in str(e):
                print(f"⚠️ LLM API not available, but error was recorded for mock testing")
                # This is expected in environments without LLM API access
                # The error will be recorded and can be replayed in mock mode
            else:
                raise
    
    @pytest.mark.asyncio
    async def test_cli_tool_direct(self):
        """Test CLI tool directly with save/mock"""
        # Simple command that should work on most systems
        result = await self.cli_tool.execute({
            "command": "echo 'Hello from CLI tool'"
        })
        
        # Verify response
        assert result is not None
        assert "Hello from CLI tool" in result["stdout"]
        
        print(f"✅ CLI tool test completed")
        print(f"   Result: {result}")

class TestToolRecordingFeatures:
    """Test the recording framework features"""
    
    def setup_method(self, method):
        """Set up test fixtures"""
        self.test_mode = get_test_mode()
        
        # Use method name to create unique test names
        test_name = f"tool_recording_{method.__name__}"
        
        self.integration_test = IntegrationTestBase(
            test_name=test_name,
            mode=self.test_mode
        )
    
    def teardown_method(self):
        if self.test_mode == IntegrationTestMode.REAL or self.test_mode == IntegrationTestMode.MOCK_THEN_REAL:
            self.integration_test.save_test_data()
    
    @pytest.mark.asyncio
    async def test_error_recording_and_playback(self):
        """Test that tool errors are properly recorded and replayed"""
        cli_tool = self.integration_test.wrap_tool(CLITool())
        # Command that should fail (non-zero exit). Now we treat failure as data, not exception.
        result = await cli_tool.execute({
            "command": "this-command-does-not-exist-12345"
        })
        assert result["returncode"] != 0
        assert not result.get("success")
        assert result["stderr"]
        print(f"✅ Error recording test completed (returncode={result['returncode']})")
    
    @pytest.mark.asyncio
    async def test_multiple_identical_calls(self):
        """Test that identical calls are handled properly"""
        cli_tool = self.integration_test.wrap_tool(CLITool())
        
        # Make the same call multiple times
        command = "echo 'test call'"
        
        result1 = await cli_tool.execute({"command": command})
        result2 = await cli_tool.execute({"command": command})
        
        # Results should be identical
        assert result1 == result2
        
        print(f"✅ Multiple identical calls test completed")
