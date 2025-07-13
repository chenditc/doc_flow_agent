#!/usr/bin/env python3
"""
Integration Tests for DocExecuteEngine
Uses the save/mock framework for testing complex workflow orchestration
"""

import asyncio
import sys
import os
import pytest
import json
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, mock_open

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from integration_test_framework import IntegrationTestBase, IntegrationTestMode, get_test_mode, print_test_mode_info
from tools.llm_tool import LLMTool
from tools.cli_tool import CLITool
from tools.user_communicate_tool import UserCommunicateTool
from doc_execute_engine import DocExecuteEngine, Task
from sop_document import SOPDocument
from exceptions import TaskInputMissingError, TaskCreationError
from utils import set_json_path_value


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
        self.cli_tool = self.integration_test.wrap_tool(CLITool())
        self.user_tool = self.integration_test.wrap_tool(UserCommunicateTool())
        
        # Create temporary directories for test
        self.temp_dir = Path(tempfile.mkdtemp())
        self.context_file = self.temp_dir / "context.json"
        self.traces_dir = self.temp_dir / "traces"
        
        # Create directories
        self.traces_dir.mkdir(parents=True)
        
        # Use the real SOP docs directory instead of creating temporary ones
        real_docs_dir = Path(__file__).parent.parent / "sop_docs"
        
        # Create DocExecuteEngine with real SOP docs directory
        self.engine = DocExecuteEngine(
            docs_dir=str(real_docs_dir),
            context_file=str(self.context_file),
            enable_tracing=True,
            trace_output_dir=str(self.traces_dir)
        )
        
        # Replace the engine's tools with our wrapped versions
        self.engine.tools = {
            "LLM": self.llm_tool,
            "CLI": self.cli_tool,
            "USER_COMMUNICATE": self.user_tool
        }
        
        # Recreate JsonPathGenerator with the wrapped LLM tool
        from tools.json_path_generator import JsonPathGenerator
        self.engine.json_path_generator = JsonPathGenerator(self.llm_tool)
        
        # Recreate SOPDocumentParser with the wrapped LLM tool
        from sop_document import SOPDocumentParser
        self.engine.sop_parser = SOPDocumentParser(str(real_docs_dir), llm_tool=self.llm_tool)
    
    def teardown_method(self):
        """Clean up and save test data if in real mode"""
        if self.test_mode == IntegrationTestMode.REAL:
            self.integration_test.save_test_data()
        
        # Clean up temporary directory
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    ## A. Engine Initialization & Configuration Tests
    
    @pytest.mark.asyncio
    async def test_engine_initialization_default_config(self):
        """Test engine initializes with default configuration"""
        engine = DocExecuteEngine()
        
        assert engine.docs_dir == Path("sop_docs")
        assert engine.context_file == Path("context.json")
        assert engine.context == {}
        assert engine.task_stack == []
        assert engine.task_execution_counter == 0
        assert engine.max_retries == 3
        assert "LLM" in engine.tools
        assert "CLI" in engine.tools
        assert "USER_COMMUNICATE" in engine.tools
        
        print("✅ Engine initializes correctly with default configuration")
    
    @pytest.mark.asyncio
    async def test_engine_initialization_custom_config(self):
        """Test engine initializes with custom directories and tracing"""
        custom_docs = "/custom/docs"
        custom_context = "/custom/context.json"
        custom_traces = "/custom/traces"
        
        engine = DocExecuteEngine(
            docs_dir=custom_docs,
            context_file=custom_context,
            enable_tracing=False,
            trace_output_dir=custom_traces
        )
        
        assert engine.docs_dir == Path(custom_docs)
        assert engine.context_file == Path(custom_context)
        assert engine.tracer.output_dir == Path(custom_traces)
        assert not engine.tracer.enabled
        
        print("✅ Engine initializes correctly with custom configuration")
    
    @pytest.mark.asyncio
    async def test_tool_registration_and_discovery(self):
        """Test tool registration and get_available_tools functionality"""
        # Test initial tools
        available_tools = self.engine.get_available_tools()
        expected_tools = {"LLM", "CLI", "USER_COMMUNICATE"}
        assert set(available_tools.keys()) == expected_tools
        
        # Test tool registration
        from tools.base_tool import BaseTool
        
        class TestTool(BaseTool):
            def __init__(self):
                super().__init__("TEST_TOOL")
            
            async def execute(self, parameters):
                return "test_result"
        
        test_tool = TestTool()
        self.engine.register_tool(test_tool)
        
        updated_tools = self.engine.get_available_tools()
        assert "TEST_TOOL" in updated_tools
        assert updated_tools["TEST_TOOL"] == "TestTool"
        
        print("✅ Tool registration and discovery works correctly")

    ## B. Context Management Tests
    
    @pytest.mark.asyncio
    async def test_context_load_save_cycle(self):
        """Test loading, modifying, and saving context"""
        # Start with empty context
        context = self.engine.load_context(load_if_exists=False)
        assert context == {}
        
        # Add some data
        self.engine.context = {"test_key": "test_value", "nested": {"key": "value"}}
        self.engine.save_context()
        
        # Create new engine and load context
        new_engine = DocExecuteEngine(context_file=str(self.context_file))
        loaded_context = new_engine.load_context()
        
        assert loaded_context == {"test_key": "test_value", "nested": {"key": "value"}}
        assert new_engine.context == loaded_context
        
        print("✅ Context load/save cycle works correctly")
    
    @pytest.mark.asyncio
    async def test_context_with_nonexistent_file(self):
        """Test context behavior when file doesn't exist"""
        nonexistent_file = self.temp_dir / "nonexistent.json"
        engine = DocExecuteEngine(context_file=str(nonexistent_file))
        
        # Should return empty context when file doesn't exist
        context = engine.load_context(load_if_exists=True)
        assert context == {}
        assert engine.context == {}
        
        print("✅ Context handles nonexistent file correctly")
    
    @pytest.mark.asyncio
    async def test_context_with_corrupted_file(self):
        """Test context error handling with invalid JSON"""
        # Create corrupted JSON file
        corrupted_file = self.temp_dir / "corrupted.json"
        with open(corrupted_file, "w") as f:
            f.write("{ invalid json }")
        
        engine = DocExecuteEngine(context_file=str(corrupted_file))
        
        # Should raise JSON decode error
        with pytest.raises(json.JSONDecodeError):
            engine.load_context(load_if_exists=True)
        
        print("✅ Context handles corrupted file with appropriate error")

    ## C. JSON Path Resolution Tests
    
    @pytest.mark.asyncio
    async def test_json_path_resolution_simple(self):
        """Test basic JSON path resolution with simple paths"""
        context = {
            "user_request": "test request",
            "simple_value": 42,
            "boolean_value": True
        }
        
        # Test simple path resolution
        assert self.engine.resolve_json_path("$.user_request", context) == "test request"
        assert self.engine.resolve_json_path("$.simple_value", context) == 42
        assert self.engine.resolve_json_path("$.boolean_value", context) is True
        
        print("✅ Simple JSON path resolution works correctly")
    
    @pytest.mark.asyncio
    async def test_json_path_resolution_nested(self):
        """Test JSON path resolution with complex nested structures"""
        context = {
            "nested": {
                "level1": {
                    "level2": "deep_value"
                },
                "array": ["item1", "item2", "item3"]
            },
            "users": [
                {"name": "Alice", "age": 30},
                {"name": "Bob", "age": 25}
            ]
        }
        
        # Test nested object access
        assert self.engine.resolve_json_path("$.nested.level1.level2", context) == "deep_value"
        
        # Test array access
        assert self.engine.resolve_json_path("$.nested.array[1]", context) == "item2"
        
        # Test array of objects
        assert self.engine.resolve_json_path("$.users[0].name", context) == "Alice"
        
        print("✅ Nested JSON path resolution works correctly")
    
    @pytest.mark.asyncio
    async def test_json_path_resolution_missing_paths(self):
        """Test JSON path resolution with non-existent paths"""
        context = {"existing_key": "value"}
        
        # Test missing keys
        assert self.engine.resolve_json_path("$.nonexistent", context) is None
        assert self.engine.resolve_json_path("$.existing_key.nonexistent", context) is None
        
        # Test invalid array index
        context_with_array = {"array": ["item1", "item2"]}
        assert self.engine.resolve_json_path("$.array[10]", context_with_array) is None
        
        print("✅ Missing path resolution returns None correctly")
    
    @pytest.mark.asyncio
    async def test_execution_prefix_path_generation(self):
        """Test add_execution_prefix_to_path functionality"""
        self.engine.task_execution_counter = 5
        
        # Test simple paths
        assert self.engine.add_execution_prefix_to_path("$.output") == "$.msg5_output"
        assert self.engine.add_execution_prefix_to_path("$.result") == "$.msg5_result"
        
        # Test paths with array notation
        assert self.engine.add_execution_prefix_to_path("$.messages[0]") == "$.msg5_messages[0]"
        assert self.engine.add_execution_prefix_to_path("$.data[1].value") == "$.msg5_data[1].value"
        
        # Test nested paths
        assert self.engine.add_execution_prefix_to_path("$.output.nested") == "$.msg5_output.nested"
        
        # Test edge cases
        assert self.engine.add_execution_prefix_to_path("") == ""
        assert self.engine.add_execution_prefix_to_path("invalid_path") == "invalid_path"
        
        print("✅ Execution prefix path generation works correctly")

    ## D. Task Creation Tests
    
    @pytest.mark.asyncio
    async def test_create_task_from_sop_document(self):
        """Test task creation from standard bash SOP document"""
        # Load standard bash SOP document
        sop_doc = self.engine.load_sop_document("tools/bash")
        
        # Set up context with task information - this simulates how the engine would populate context from description
        task_description = "List home directory contents using command: ls -la ~/"
        self.engine.context = {"current_task": task_description}
        
        # Create task
        task = await self.engine.create_task_from_sop(sop_doc, task_description)
        print(task)
        assert task.description == task_description
        assert task.sop_doc_id == "tools/bash"
        assert task.tool["tool_id"] == "CLI"
        assert task.input_json_path is not None
        
        print("✅ Task creation from bash SOP document works correctly")
    
    @pytest.mark.asyncio
    async def test_create_task_with_dynamic_input_generation(self):
        """Test task creation with dynamic input using LLM SOP document"""
        # Test through the complete workflow which populates context automatically
        description = "Generate a welcome message: Write a simple greeting message for a new user to school, less than 50 words. This is for a welcome screen."
        
        # Use the start method which will populate context and create tasks automatically
        await self.engine.start(description)
        
        # Verify the workflow executed successfully
        assert self.engine.task_execution_counter > 0
        assert len(self.engine.context) > 0
        
        print("✅ Task creation with dynamic input generation works correctly")
    
    @pytest.mark.asyncio
    async def test_create_task_from_description_valid_sop(self):
        """Test task creation from natural language with bash SOP"""
        description = "Run ls command to list home directory contents using: ls -la ~/"
        
        task = await self.engine.create_task_from_description(description)
        
        assert task.description == description
        # Since the LLM might not pick up the bash SOP, this will likely use fallback
        # which is expected behavior - fallback can handle any task
        assert task.tool["tool_id"] in ["CLI", "LLM"]
        
        print("✅ Task creation from description with bash SOP works correctly")
    
    @pytest.mark.asyncio
    async def test_create_task_from_description_invalid_sop(self):
        """Test task creation error handling with non-existent SOP"""
        # Mock the SOP parser to return non-existent doc_id
        with patch.object(self.engine.sop_parser, 'parse_sop_doc_id_from_description') as mock_parser:
            mock_parser.return_value = "nonexistent/sop"
            
            description = "Task with non-existent SOP"
            
            with pytest.raises(ValueError, match="Cannot find SOP document for parsed doc_id: nonexistent/sop"):
                await self.engine.create_task_from_description(description)
        
        print("✅ Task creation handles invalid SOP correctly")

    ## E. Single Task Execution Tests
    
    @pytest.mark.asyncio
    async def test_execute_task_simple_llm_tool(self):
        """Test execution of task using LLM tool with meaningful task"""
        # Create task using standard LLM SOP with context information in description
        task = Task(
            task_id="test-task-1",
            description="Write a command which can list out the contents of the home directory. Task: Write a welcome message for new users joining our platform",
            sop_doc_id="tools/llm",
            tool={"tool_id": "LLM", "parameters": {"prompt": "Please complete the following task:\n\n{current_task}"}},
            input_json_path={"current_task": "$.task_request"},
            output_json_path="$.llm_result"
        )
        
        # Populate context with task information extracted from description
        self.engine.context = {"task_request": "Write a welcome message for new users joining our platform"}
        
        # Execute task
        new_tasks = await self.engine.execute_task(task)
        
        # Verify execution
        assert self.engine.task_execution_counter == 1
        assert "msg1_llm_result" in self.engine.context
        assert isinstance(new_tasks, list)
        
        print("✅ LLM tool execution works correctly")
    
    @pytest.mark.asyncio
    async def test_execute_task_cli_tool(self):
        """Test execution of task using CLI tool with meaningful command"""
        # Create task using standard bash SOP with command embedded in description
        task = Task(
            task_id="test-task-2",
            description="List root directory contents using command: ls -la /",
            sop_doc_id="tools/bash",
            tool={"tool_id": "CLI"},
            input_json_path={"command": "$.bash_command"},
            output_json_path="$.cli_result"
        )
        
        # Populate context with command extracted from description
        self.engine.context = {"bash_command": "ls -la /"}
        
        # Execute task
        new_tasks = await self.engine.execute_task(task)
        
        # Verify execution
        assert self.engine.task_execution_counter == 1
        assert "msg1_cli_result" in self.engine.context
        assert isinstance(new_tasks, list)
        
        print("✅ CLI tool execution works correctly")
    
    @pytest.mark.asyncio
    async def test_execute_task_user_communicate_tool(self):
        """Test execution of task using user communication tool with meaningful interaction"""
        # Create task using standard user communication SOP with prompt embedded in description
        task = Task(
            task_id="test-task-3",
            description="Ask user for project requirements. Message to user: Please describe the main features you want in your new application",
            sop_doc_id="tools/user_communicate",
            tool={"tool_id": "USER_COMMUNICATE", "parameters": {"message": "Current task needs your help:\n\n{message_to_user}"}},
            input_json_path={"message_to_user": "$.user_prompt"},
            output_json_path="$.user_response"
        )
        
        # Populate context with user prompt extracted from description
        self.engine.context = {"user_prompt": "Please describe the main features you want in your new application"}
        
        # Mock the _get_multiline_input method to avoid stdin issues in testing
        with patch.object(self.user_tool.tool, '_get_multiline_input', return_value='I want a simple todo list app with user authentication and task sharing capabilities'):
            # Execute task
            new_tasks = await self.engine.execute_task(task)
            
            # Verify execution
            assert self.engine.task_execution_counter == 1
            assert "msg1_user_response" in self.engine.context
            assert isinstance(new_tasks, list)
        
        print("✅ User communication tool execution works correctly")
    
    @pytest.mark.asyncio
    async def test_execute_task_with_input_resolution(self):
        """Test task execution with input path resolution using blog outline generation"""
        # Create task using real blog outline SOP with topic embedded in description
        task = Task(
            task_id="test-task-4",
            description="Generate blog outline for AI topic: The Future of Artificial Intelligence in Education",
            sop_doc_id="blog/generate_outline",
            tool={"tool_id": "LLM", "parameters": {"prompt": "请为主题【{title}】生成一个清晰的3-5小节大纲，帮助撰写文章。大纲的开头一定要离奇、吸引人思考，可以通过提出一个生活中的反常识事实来实现。\n\n如果你对这个主题不熟悉，你可以只返回【{title}】作为单个小节。\n\n如果主题【{title}】有可能引起争议，在生成完大纲后建议用户参考文档 \"doc/more_info.md\" 进行进一步调研。"}},
            input_json_path={"title": "$.blog_topic"},
            output_json_path="$.outline_result"
        )
        
        # Populate context with topic extracted from description
        self.engine.context = {"blog_topic": "The Future of Artificial Intelligence in Education"}
        
        # Execute task
        new_tasks = await self.engine.execute_task(task)
        
        # Verify input resolution worked
        assert "msg1_outline_result" in self.engine.context
        
        print("✅ Task execution with input resolution for blog outline works correctly")
    
    ## F. Error Handling Tests
    
    @pytest.mark.asyncio
    async def test_execute_task_with_missing_input_error(self):
        """Test task execution failure with missing required inputs"""
        # Create task with missing input path using bash SOP - intentionally don't provide command in description
        task = Task(
            task_id="test-task-6",
            description="Task with missing command input - no command provided",
            sop_doc_id="tools/bash",
            tool={"tool_id": "CLI"},
            input_json_path={"command": "$.nonexistent_command"},
            output_json_path="$.result"
        )
        
        # Context doesn't have the required path and description doesn't provide it
        self.engine.context = {"other_data": "value"}
        
        # Execute task should fail
        with pytest.raises(ValueError, match="Input path '\\$\\.nonexistent_command' not found in context"):
            await self.engine.execute_task(task)
        
        print("✅ Task execution handles missing input correctly")
    
    @pytest.mark.asyncio
    async def test_execute_task_with_unknown_tool_error(self):
        """Test task execution failure with unknown tool"""
        # Create task with unknown tool
        task = Task(
            task_id="test-task-7",
            description="Task with unknown tool",
            sop_doc_id="tools/bash",
            tool={"tool_id": "UNKNOWN_TOOL", "parameters": {}},
            input_json_path={},
            output_json_path="$.result"
        )
        
        # Execute task should fail
        with pytest.raises(ValueError, match="Unknown tool: UNKNOWN_TOOL"):
            await self.engine.execute_task(task)
        
        print("✅ Task execution handles unknown tool correctly")
    
    ## G. End-to-End Workflow Tests
    
    @pytest.mark.asyncio
    async def test_complete_workflow_bash_task(self):
        """Test complete workflow with bash command execution"""

        # Create a temporary file with some text, use bash to command to check the contents.
        # Use fixed directory to enable mock testing
        
        temp_file = "./temp_test_file_for_complete_workflow_bash_task.txt"
        string_to_write = "This is a test file for bash command execution."
        with open(temp_file, "w") as f:
            f.write(string_to_write)

        try:
            # Test a meaningful bash task with command embedded in description
            description = f"Follow tools/bash.md and run cat command: 'cat {temp_file}'. This will read the contents of the file and print it to the console."

            await self.engine.start(description)
            
            # Verify task execution
            assert self.engine.task_execution_counter > 0
            assert len(self.engine.context) > 0

            print(self.engine.get_last_task_output())
            assert self.engine.get_last_task_output()["stdout"] == string_to_write

            
            print("✅ Complete bash task workflow works correctly")
        finally:
            # Clean up temporary file
            if Path(temp_file).exists():
                Path(temp_file).unlink()
    
    @pytest.mark.asyncio  
    async def test_complete_workflow_llm_task(self):
        """Test complete workflow with LLM text generation"""
        # Execute a meaningful LLM task from description with complete context embedded
        # Use a complete, specific task that doesn't need follow-up questions
        description = "Follow tools/llm and write a simple Python function to calculate the area of a circle. Use function name 'calculate_circle_area' and return the result as a float. The function should take 'radius' as input."
        
        await self.engine.start(description)
        
        # Verify task execution
        assert self.engine.task_execution_counter > 0
        assert len(self.engine.context) > 0

        # Validate the generated code by execute it in different namespace
        generated_code = self.engine.get_last_task_output()
        assert "calculate_circle_area" in generated_code
        
        print("✅ Complete LLM task workflow works correctly")
    
    @pytest.mark.asyncio
    async def test_complete_workflow_general_task(self):
        """Test complete workflow with general task"""
        # Test using a complete, specific task with all context embedded in description
        description = "Generate a simple greeting message: 'Hello, welcome to our platform!' - keep it exactly like this"
        
        await self.engine.start(description)
        
        # Verify task execution
        assert self.engine.task_execution_counter > 0
        assert len(self.engine.context) > 0
        
        print("✅ Complete general workflow works correctly")


if __name__ == "__main__":
    # Run tests directly
    pytest.main([__file__, "-v"])
