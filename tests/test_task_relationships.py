#!/usr/bin/env python3
"""
Test Phase 1 Task Relationship Features

This test file specifically validates the Phase 1 enhancements to task relationship tracking,
including PendingTask objects, task relationships, and enhanced tracing.
"""

import asyncio
import pytest
from unittest.mock import patch, MagicMock
import uuid
import re

from doc_execute_engine import DocExecuteEngine, Task, PendingTask
from tracing import ExecutionTracer


class TestTaskRelationships:
    """Test Phase 1 task relationship features"""

    def setup_method(self):
        """Set up test environment"""
        self.engine = DocExecuteEngine(enable_tracing=True, trace_output_dir="test_traces")

    def test_pending_task_creation(self):
        """Test PendingTask dataclass creation and auto-generation"""
        # Test with minimal fields
        pending_task = PendingTask(description="Test task description")
        # Verify auto-generated fields (deterministic hash id)
        assert pending_task.task_id is not None
        assert len(pending_task.task_id) == 16  # First 16 hex chars of sha1
        assert re.fullmatch(r"[0-9a-f]{16}", pending_task.task_id)
        assert pending_task.short_name == "Test task description"
        assert pending_task.parent_task_id is None
        assert pending_task.generated_by_phase is None

        # Test with long description
        long_description = "This is a very long task description that should be truncated to 50 characters max for the short name"
        pending_task_long = PendingTask(description=long_description)
        assert len(pending_task_long.short_name) == 50
        assert pending_task_long.short_name.endswith("...")

        print("✅ PendingTask creation and auto-generation works correctly")

    def test_pending_task_with_relationships(self):
        """Test PendingTask with parent-child relationships"""
        # Create parent task
        parent_task = PendingTask(description="Parent task")
        
        # Create child task
        child_task = PendingTask(
            description="Child task",
            parent_task_id=parent_task.task_id,
            generated_by_phase="new_task_generation"
        )
        
        # Verify relationships
        assert child_task.parent_task_id == parent_task.task_id
        assert child_task.generated_by_phase == "new_task_generation"
        assert parent_task.parent_task_id is None  # Root task
        
        print("✅ PendingTask parent-child relationships work correctly")

    def test_task_with_enhanced_fields(self):
        """Test Task class with new relationship fields"""
        task = Task(
            task_id="test-task-id",
            description="Test task",
            sop_doc_id="tools/llm",
            tool={"tool_id": "LLM"},
            input_json_path={"input": "$.test"},
            output_json_path="$.output",
            parent_task_id="parent-task-id"
        )
        
        # Verify new fields
        assert task.short_name is not None  # Auto-generated
        assert task.parent_task_id == "parent-task-id"
        
        # Test __str__ method includes new fields
        task_str = str(task)
        assert "Short Name:" in task_str
        assert "Parent Task ID:" in task_str
        
        # Test __repr__ method includes new fields  
        task_repr = repr(task)
        assert "short_name=" in task_repr
        assert "parent_task_id=" in task_repr
        
        print("✅ Task class enhanced fields work correctly")

    def test_engine_task_stack_with_pending_tasks(self):
        """Test DocExecuteEngine task stack with PendingTask objects"""
        # Verify task stack is properly typed
        assert isinstance(self.engine.task_stack, list)
        assert isinstance(self.engine.pending_tasks, dict)
        
        # Add PendingTask objects
        pending_task1 = PendingTask(description="First task")
        pending_task2 = PendingTask(description="Second task")
        
        # Test add_new_tasks method
        asyncio.run(self.engine.add_new_tasks([pending_task1, pending_task2]))
        
        # Verify tasks are in stack (in reverse order)
        assert len(self.engine.task_stack) == 2
        assert self.engine.task_stack[0] == pending_task2  # Last added, first to pop
        assert self.engine.task_stack[1] == pending_task1
        
        # Verify tasks are indexed
        assert self.engine.pending_tasks[pending_task1.task_id] == pending_task1
        assert self.engine.pending_tasks[pending_task2.task_id] == pending_task2
        
        print("✅ Engine task stack with PendingTask objects works correctly")

    def test_engine_state_with_pending_tasks(self):
        """Test _get_engine_state method with PendingTask objects"""
        # Clear task stack first
        self.engine.task_stack.clear()
        
        # Add some PendingTask objects to stack
        pending_task = PendingTask(description="Test task")
        self.engine.task_stack.append(pending_task)
        
        # Get engine state
        state = self.engine._get_engine_state()
        
        # Verify PendingTask is serialized to dict
        assert len(state["task_stack"]) == 1
        task_data = state["task_stack"][0]
        assert isinstance(task_data, dict)
        assert task_data["description"] == "Test task"
        assert task_data["task_id"] == pending_task.task_id
        assert task_data["short_name"] == pending_task.short_name
        
        print("✅ Engine state serialization with PendingTask objects works correctly")

    @pytest.mark.asyncio
    async def test_create_task_from_pending_task(self):
        """Test creating Task from PendingTask with relationship tracking"""
        # Set up context with the bash command needed for the task
        self.engine.context = {
            "current_task": "Create test file using bash",
            "command": "touch test.txt"  # Provide the specific bash command needed
        }
        
        # Create PendingTask with relationships
        parent_id = str(uuid.uuid4())
        pending_task = PendingTask(
            description="Create test file using bash",
            parent_task_id=parent_id,
            generated_by_phase="new_task_generation"
        )
        
        # Mock the SOP resolution to use bash SOP
        with patch.object(self.engine.sop_parser, 'parse_sop_doc_id_from_description') as mock_parser:
            mock_parser.return_value = ("tools/bash", "")
            
            # Create task from PendingTask
            task = await self.engine.create_task_from_description(pending_task)
            
            # Verify task inherits relationship data
            assert task.task_id == pending_task.task_id
            assert task.short_name == pending_task.short_name  
            assert task.parent_task_id == parent_id
            assert task.description == pending_task.description
            assert task.sop_doc_id == "tools/bash"
        
        print("✅ Task creation from PendingTask with relationships works correctly")

    @pytest.mark.asyncio
    async def test_parse_new_tasks_returns_pending_tasks(self):
        """Test that parse_new_tasks_from_output returns PendingTask objects"""
        # Create a sample task
        parent_task = Task(
            task_id="parent-id",
            description="Parent task",
            sop_doc_id="tools/llm",
            tool={"tool_id": "LLM"},
            input_json_path={},
            output_json_path="$.output"
        )
        
        # Mock LLM response with tool call
        mock_response = {
            "tool_calls": [
                {
                    "name": "extract_new_tasks",
                    "arguments": {
                        "tasks": ["Task 1: Do something important", "Task 2: Do something else"]
                    }
                }
            ]
        }
        
        # Mock LLM tool
        with patch.object(self.engine.tools["LLM"], 'execute') as mock_llm:
            mock_llm.return_value = mock_response
            
            # Call parse_new_tasks_from_output
            output = "Some tool output that suggests new tasks"
            new_pending_tasks = await self.engine.parse_new_tasks_from_output(output, parent_task)
            
            # Verify returned objects are PendingTask instances
            assert len(new_pending_tasks) == 2
            for pending_task in new_pending_tasks:
                assert isinstance(pending_task, PendingTask)
                assert pending_task.parent_task_id == parent_task.task_id
                assert pending_task.generated_by_phase == "new_task_generation"
                assert pending_task.task_id is not None
                assert pending_task.short_name is not None
        
        print("✅ parse_new_tasks_from_output returns PendingTask objects correctly")

    @pytest.mark.asyncio 
    async def test_initial_task_creates_pending_task(self):
        """Test that start() method creates PendingTask for initial task"""
        initial_description = "Initial test task"
        
        # Mock the execution to prevent actual task running
        with patch.object(self.engine, 'create_task_from_description') as mock_create, \
             patch.object(self.engine, 'run_task') as mock_run:
            
            # Mock task creation and execution
            mock_task = Task(
                task_id="test-id",
                description=initial_description,
                sop_doc_id="general/fallback",
                tool={"tool_id": "LLM"},
                input_json_path={},
                output_json_path="$.output"
            )
            mock_create.return_value = mock_task
            mock_run.return_value = []  # No new tasks
            
            # Start engine with initial task
            await self.engine.start(initial_description)
            
            # Verify create_task_from_description was called with PendingTask
            mock_create.assert_called_once()
            call_args = mock_create.call_args[0]
            pending_task_arg = call_args[0]
            assert isinstance(pending_task_arg, PendingTask)
            assert pending_task_arg.description == initial_description
            assert pending_task_arg.parent_task_id is None  # Root task
        
        print("✅ Initial task creates PendingTask correctly")


if __name__ == "__main__":
    pytest.main([__file__])
