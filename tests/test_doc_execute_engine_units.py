#!/usr/bin/env python3
"""
Unit Tests for DocExecuteEngine isolated components
Tests for methods that can be tested in isolation without complex dependencies
"""

import unittest
import sys
import os
import json
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from doc_execute_engine import DocExecuteEngine, Task


class TestDocExecuteEngineUnits(unittest.TestCase):
    """Unit tests for isolated DocExecuteEngine methods"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.engine = DocExecuteEngine()
    
    def test_template_rendering_basic(self):
        """Test basic template rendering with {var} syntax"""
        template = "Hello {name}, welcome to {place}!"
        variables = {"name": "Alice", "place": "Wonderland"}
        
        result = self.engine.render_template(template, variables)
        
        self.assertEqual(result, "Hello Alice, welcome to Wonderland!")
    
    def test_template_rendering_missing_variables(self):
        """Test template rendering with missing variables"""
        template = "Process {available} and {missing}"
        variables = {"available": "data"}
        
        result = self.engine.render_template(template, variables)
        
        # Missing variables should remain as template placeholders
        self.assertEqual(result, "Process data and {missing}")
    
    def test_template_rendering_empty_variables(self):
        """Test template rendering with empty variables dict"""
        template = "No variables to replace"
        variables = {}
        
        result = self.engine.render_template(template, variables)
        
        self.assertEqual(result, "No variables to replace")
    
    def test_template_rendering_special_characters(self):
        """Test template rendering with special characters"""
        template = "Command: {command}"
        variables = {"command": "echo 'Hello & goodbye!'"}
        
        result = self.engine.render_template(template, variables)
        
        self.assertEqual(result, "Command: echo 'Hello & goodbye!'")
    
    def test_template_rendering_numeric_values(self):
        """Test template rendering with numeric values"""
        template = "Age: {age}, Score: {score}, Active: {active}"
        variables = {"age": 25, "score": 95.5, "active": True}
        
        result = self.engine.render_template(template, variables)
        
        self.assertEqual(result, "Age: 25, Score: 95.5, Active: True")
    
    def test_json_path_prefix_generation_simple(self):
        """Test execution prefix path generation with simple paths"""
        self.engine.task_execution_counter = 3
        
        test_cases = [
            # Prefixing behavior removed in engine; now paths remain unchanged
            ("$.output", "$.output"),
            ("$.result", "$.result"),
            ("$.data", "$.data"),
        ]
        
        for input_path, expected in test_cases:
            with self.subTest(input_path=input_path):
                result = self.engine.add_execution_prefix_to_path(input_path)
                self.assertEqual(result, expected)
    
    def test_json_path_prefix_generation_arrays(self):
        """Test execution prefix path generation with array notation"""
        self.engine.task_execution_counter = 7
        
        test_cases = [
            ("$.messages[0]", "$.messages[0]"),
            ("$.items[5]", "$.items[5]"),
            ("$.users[10].name", "$.users[10].name"),
        ]
        
        for input_path, expected in test_cases:
            with self.subTest(input_path=input_path):
                result = self.engine.add_execution_prefix_to_path(input_path)
                self.assertEqual(result, expected)
    
    def test_json_path_prefix_generation_nested(self):
        """Test execution prefix path generation with nested paths"""
        self.engine.task_execution_counter = 12
        
        test_cases = [
            ("$.output.nested", "$.output.nested"),
            ("$.data.level1.level2", "$.data.level1.level2"),
            ("$.result.summary.count", "$.result.summary.count"),
        ]
        
        for input_path, expected in test_cases:
            with self.subTest(input_path=input_path):
                result = self.engine.add_execution_prefix_to_path(input_path)
                self.assertEqual(result, expected)
    
    def test_json_path_prefix_generation_edge_cases(self):
        """Test execution prefix path generation with edge cases"""
        self.engine.task_execution_counter = 1
        
        test_cases = [
            ("", ""),  # Empty string
            ("invalid_path", "invalid_path"),  # No $ prefix
            ("$.", "$."),  # Just root
            ("$..", "$.."),  # Double dot (returns as-is due to empty first key)
        ]
        
        for input_path, expected in test_cases:
            with self.subTest(input_path=input_path):
                result = self.engine.add_execution_prefix_to_path(input_path)
                self.assertEqual(result, expected)
    
    def test_json_path_resolution_simple_values(self):
        """Test JSON path resolution with simple values"""
        context = {
            "string_value": "hello",
            "number_value": 42,
            "boolean_value": True,
            "null_value": None
        }
        
        test_cases = [
            ("$.string_value", "hello"),
            ("$.number_value", 42),
            ("$.boolean_value", True),
            ("$.null_value", None),
        ]
        
        for path, expected in test_cases:
            with self.subTest(path=path):
                result = self.engine.resolve_json_path(path, context)
                self.assertEqual(result, expected)
    
    def test_json_path_resolution_nested_objects(self):
        """Test JSON path resolution with nested objects"""
        context = {
            "user": {
                "profile": {
                    "name": "John",
                    "age": 30
                },
                "preferences": {
                    "theme": "dark",
                    "notifications": True
                }
            }
        }
        
        test_cases = [
            ("$.user.profile.name", "John"),
            ("$.user.profile.age", 30),
            ("$.user.preferences.theme", "dark"),
            ("$.user.preferences.notifications", True),
        ]
        
        for path, expected in test_cases:
            with self.subTest(path=path):
                result = self.engine.resolve_json_path(path, context)
                self.assertEqual(result, expected)
    
    def test_json_path_resolution_arrays(self):
        """Test JSON path resolution with arrays"""
        context = {
            "items": ["first", "second", "third"],
            "users": [
                {"name": "Alice", "id": 1},
                {"name": "Bob", "id": 2}
            ]
        }
        
        test_cases = [
            ("$.items[0]", "first"),
            ("$.items[2]", "third"),
            ("$.users[0].name", "Alice"),
            ("$.users[1].id", 2),
        ]
        
        for path, expected in test_cases:
            with self.subTest(path=path):
                result = self.engine.resolve_json_path(path, context)
                self.assertEqual(result, expected)
    
    def test_json_path_resolution_missing_paths(self):
        """Test JSON path resolution with missing paths"""
        context = {
            "existing": {
                "nested": "value"
            },
            "array": ["item1", "item2"]
        }
        
        missing_paths = [
            "$.nonexistent",
            "$.existing.missing",
            "$.existing.nested.deeper",
            "$.array[10]",
            "$.array.missing",
        ]
        
        for path in missing_paths:
            with self.subTest(path=path):
                result = self.engine.resolve_json_path(path, context)
                self.assertIsNone(result)
    
    def test_json_path_resolution_invalid_syntax(self):
        """Test JSON path resolution with invalid syntax"""
        context = {"valid": "data"}
        
        # Invalid JSON paths should return None (handled gracefully)
        invalid_paths = [
            "invalid_syntax",
            "$.{invalid}",
            "$.[invalid]",
        ]
        
        for path in invalid_paths:
            with self.subTest(path=path):
                result = self.engine.resolve_json_path(path, context)
                self.assertIsNone(result)
    
    def test_task_dataclass_creation(self):
        """Test Task dataclass creation and validation"""
        task = Task(
            task_id="test-123",
            description="Test task description",
            sop_doc_id="general/test",
            tool={"tool_id": "LLM", "parameters": {"param": "value"}},
            input_json_path={"input": "$.data"},
            output_json_path="$.result",
            output_description="Test output description"
        )
        
        self.assertEqual(task.task_id, "test-123")
        self.assertEqual(task.description, "Test task description")
        self.assertEqual(task.sop_doc_id, "general/test")
        self.assertEqual(task.tool["tool_id"], "LLM")
        self.assertEqual(task.input_json_path["input"], "$.data")
        self.assertEqual(task.output_json_path, "$.result")
        self.assertEqual(task.output_description, "Test output description")
    
    def test_task_dataclass_string_representation(self):
        """Test Task dataclass string representation"""
        task = Task(
            task_id="test-456",
            description="String repr test",
            sop_doc_id="general/string_test",
            tool={"tool_id": "CLI"},
            input_json_path={"cmd": "$.command"},
            output_json_path="$.output"
        )
        
        # Test __str__ method
        str_repr = str(task)
        self.assertIn("test-456", str_repr)
        self.assertIn("String repr test", str_repr)
        self.assertIn("general/string_test", str_repr)
        self.assertIn("CLI", str_repr)
        
        # Test __repr__ method
        repr_str = repr(task)
        self.assertIn("Task(", repr_str)
        self.assertIn("task_id=test-456", repr_str)
    
    def test_get_engine_state(self):
        """Test engine state capture for tracing"""
        from doc_execute_engine import PendingTask
        
        # Set up some engine state with PendingTask objects
        task1 = PendingTask(description="task1")
        task2 = PendingTask(description="task2")
        self.engine.task_stack = [task1, task2]
        self.engine.context = {"key": "value", "nested": {"data": 123}}
        self.engine.task_execution_counter = 5
        
        state = self.engine._get_engine_state()
        
        # Verify state capture - PendingTask objects are converted to dict format
        self.assertEqual(len(state["task_stack"]), 2)
        self.assertEqual(state["task_stack"][0]["description"], "task1")
        self.assertEqual(state["task_stack"][1]["description"], "task2")
        # Verify that task_id and short_name are included
        self.assertIn("task_id", state["task_stack"][0])
        self.assertIn("short_name", state["task_stack"][0])
        self.assertEqual(state["context"]["key"], "value")
        self.assertEqual(state["context"]["nested"]["data"], 123)
        self.assertEqual(state["task_execution_counter"], 5)
        
        # Verify it's a deep copy (modifying original shouldn't affect state)
        self.engine.task_stack.append("task3")
        self.engine.context["new_key"] = "new_value"
        
        # State should remain unchanged
        self.assertEqual(len(state["task_stack"]), 2)
        self.assertNotIn("new_key", state["context"])
    
    def test_get_available_tools_empty(self):
        """Test get_available_tools with empty tools dict"""
        engine = DocExecuteEngine()
        engine.tools = {}
        
        tools = engine.get_available_tools()
        
        self.assertEqual(tools, {})
    
    def test_get_available_tools_with_tools(self):
        """Test get_available_tools with registered tools"""
        # Mock tools for testing
        class MockLLMTool:
            pass
        
        class MockCLITool:
            pass
        
        engine = DocExecuteEngine()
        engine.tools = {
            "LLM": MockLLMTool(),
            "CLI": MockCLITool()
        }
        
        tools = engine.get_available_tools()
        
        expected = {
            "LLM": "MockLLMTool",
            "CLI": "MockCLITool"
        }
        self.assertEqual(tools, expected)
    
    @patch('builtins.open', new_callable=unittest.mock.mock_open, read_data='{"test": "data"}')
    @patch('pathlib.Path.exists', return_value=True)
    def test_load_context_existing_file(self, mock_exists, mock_open_file):
        """Test loading context from existing file"""
        engine = DocExecuteEngine()
        
        context = engine.load_context(load_if_exists=True)
        
        self.assertEqual(context, {"test": "data"})
        self.assertEqual(engine.context, {"test": "data"})
        mock_open_file.assert_any_call(engine.context_file, 'r', encoding='utf-8')

    @patch('pathlib.Path.exists', return_value=False)
    def test_load_context_nonexistent_file(self, mock_exists):
        """Test loading context when file doesn't exist"""
        engine = DocExecuteEngine()
        
        context = engine.load_context(load_if_exists=True)
        
        self.assertEqual(context, {})
        self.assertEqual(engine.context, {})
    
    def test_load_context_ignore_existing(self):
        """Test loading context with load_if_exists=False"""
        engine = DocExecuteEngine()
        
        context = engine.load_context(load_if_exists=False)
        
        self.assertEqual(context, {})
        self.assertEqual(engine.context, {})
    
    @patch('builtins.open', new_callable=unittest.mock.mock_open)
    @patch('json.dump')
    def test_save_context(self, mock_json_dump, mock_open_file):
        """Test saving context to file"""
        engine = DocExecuteEngine()
        engine.context = {"save_test": "data", "number": 42}
        
        engine.save_context()
        
        mock_open_file.assert_any_call(engine.context_file, 'w', encoding='utf-8')
        mock_json_dump.assert_called_once()
        
        # Verify json.dump was called with correct parameters
        call_args = mock_json_dump.call_args
        self.assertEqual(call_args[0][0], {"save_test": "data", "number": 42})
        self.assertEqual(call_args[1]["ensure_ascii"], False)
        self.assertEqual(call_args[1]["indent"], 2)

    def test_last_task_output_initialization(self):
        """Test that last_task_output is initialized to None"""
        engine = DocExecuteEngine()
        
        # Should be None initially
        self.assertIsNone(engine.get_last_task_output())
        self.assertIsNone(engine.last_task_output)

    def test_last_task_output_getter(self):
        """Test the get_last_task_output method"""
        engine = DocExecuteEngine()
        
        # Test initial state
        self.assertIsNone(engine.get_last_task_output())
        
        # Manually set a value and test getter
        test_output = {"test": "output", "result": 123}
        engine.last_task_output = test_output
        
        result = engine.get_last_task_output()
        self.assertEqual(result, test_output)
        
        # Test with different data types
        string_output = "Simple string output"
        engine.last_task_output = string_output
        self.assertEqual(engine.get_last_task_output(), string_output)
        
        list_output = [1, 2, 3, "test"]
        engine.last_task_output = list_output
        self.assertEqual(engine.get_last_task_output(), list_output)

    # New tests for max_tasks feature
    def test_engine_max_tasks_zero(self):
        """Engine with max_tasks=0 should execute nothing even if initial task provided"""
        engine = DocExecuteEngine(max_tasks=0)
        # Add one pending task manually and start
        import asyncio
        asyncio.run(engine.start("Simple greeting task: Say hello"))
        self.assertEqual(engine.task_execution_counter, 0)
        self.assertTrue(engine.context.get('max_tasks_reached'))

    @patch("doc_execute_engine.SmartJsonPathGenerator.generate_output_json_path", new_callable=AsyncMock)
    @patch.object(DocExecuteEngine, "generate_short_names_for_pending_tasks", new_callable=AsyncMock)
    @patch.object(DocExecuteEngine, "save_context")
    @patch("doc_execute_engine.LLMTool")
    def test_compact_subtree_success(self, mock_llm_cls, mock_save_context, mock_generate_short_names, mock_generate_output_path):
        """Compact subtree should synthesize artifact and prune original keys when requirements met."""
        mock_llm_instance = MagicMock()
        mock_llm_instance.execute = AsyncMock()
        mock_llm_cls.return_value = mock_llm_instance

        engine = DocExecuteEngine(enable_tracing=False)
        engine.context = {
            "root_output": {"summary": "draft"},
            "child_output": "details"
        }

        root_task = Task(
            task_id="root",
            description="Produce final answer",
            sop_doc_id="dummy/root",
            tool={"tool_id": "LLM"},
            input_json_path={},
            output_json_path="$.root_output",
            output_description="Root output"
        )
        child_task = Task(
            task_id="child",
            description="Gather details",
            sop_doc_id="dummy/child",
            tool={"tool_id": "LLM"},
            input_json_path={},
            output_json_path="$.child_output",
            output_description="Child output",
            parent_task_id="root"
        )
        engine.completed_tasks = {"root": root_task, "child": child_task}
        engine.pending_tasks = {}
        engine.task_stack = []

        engine.tools["LLM"].execute = AsyncMock(return_value={
            "tool_calls": [
                {
                    "name": "evaluate_and_summarize_subtree",
                    "arguments": {
                        "requirements_met": True,
                        "summary": "All objectives are satisfied.",
                        "check_requirement_one_by_one": "All requirements checked and satisfied",
                        "deliverable_output_path": ["$.root_output", "$.child_output"]
                    }
                }
            ]
        })
        mock_generate_output_path.return_value = "$.compacted_result"

        result = asyncio.run(engine._compact_subtree("root"))

        self.assertTrue(result)
        self.assertIn("compacted_result", engine.context)
        artifact = engine.context["compacted_result"]
        self.assertEqual(artifact["summary"], "All objectives are satisfied.")
        expected_useful = {"root_output": {"summary": "draft"}, "child_output": "details"}
        self.assertEqual(artifact["compacted_output"], expected_useful)
        self.assertNotIn("root_output", engine.context)
        self.assertNotIn("child_output", engine.context)
        self.assertEqual(root_task.output_json_path, "$.compacted_result")
        self.assertEqual(engine.last_task_output["summary"], "All objectives are satisfied.")
        mock_generate_output_path.assert_awaited_once()
        mock_save_context.assert_called()

    @patch("doc_execute_engine.SmartJsonPathGenerator.generate_output_json_path", new_callable=AsyncMock)
    @patch.object(DocExecuteEngine, "generate_short_names_for_pending_tasks", new_callable=AsyncMock)
    @patch.object(DocExecuteEngine, "save_context")
    @patch("doc_execute_engine.LLMTool")
    def test_compact_subtree_unmet_requirements(self, mock_llm_cls, mock_save_context, mock_generate_short_names, mock_generate_output_path):
        """When requirements are not met, engine should enqueue follow-up tasks and skip compaction."""
        mock_llm_instance = MagicMock()
        mock_llm_instance.execute = AsyncMock()
        mock_llm_cls.return_value = mock_llm_instance

        engine = DocExecuteEngine(enable_tracing=False)
        engine.context = {
            "root_output": "draft",
            "child_output": "needs more work"
        }

        root_task = Task(
            task_id="root",
            description="Finalize report",
            sop_doc_id="dummy/root",
            tool={"tool_id": "LLM"},
            input_json_path={},
            output_json_path="$.root_output",
            output_description="Root output"
        )
        child_task = Task(
            task_id="child",
            description="Collect data",
            sop_doc_id="dummy/child",
            tool={"tool_id": "LLM"},
            input_json_path={},
            output_json_path="$.child_output",
            output_description="Child output",
            parent_task_id="root"
        )
        engine.completed_tasks = {"root": root_task, "child": child_task}
        engine.pending_tasks = {}
        engine.task_stack = []

        engine.tools["LLM"].execute = AsyncMock(return_value={
            "tool_calls": [
                {
                    "name": "evaluate_and_summarize_subtree",
                    "arguments": {
                        "check_requirement_one_by_one": "Requirement analysis shows final summary is missing",
                        "requirements_met": False,
                        "missing_requirements": ["完成最终总结"],
                        "new_task_to_execute": ["<new_task_to_execute>Follow llm.md to 完成最终总结</new_task_to_execute>"]
                    }
                }
            ]
        })

        result = asyncio.run(engine._compact_subtree("root"))

        self.assertFalse(result)
        self.assertIn("root_output", engine.context)
        self.assertIn("child_output", engine.context)
        self.assertEqual(len(engine.task_stack), 1)
        next_task = engine.task_stack[-1]
        self.assertIn("<new_task_to_execute>Follow llm.md", next_task.description)
        self.assertEqual(next_task.parent_task_id, "root")
        mock_generate_short_names.assert_awaited_once()
        mock_generate_output_path.assert_not_awaited()
        mock_save_context.assert_not_called()

    @patch.object(DocExecuteEngine, "_attempt_subtree_compaction", new_callable=AsyncMock)
    @patch.object(DocExecuteEngine, "parse_new_tasks_from_output", new_callable=AsyncMock)
    def test_execute_task_injects_planning_metadata(self, mock_parse_new_tasks, mock_compaction):
        """general/plan tasks should receive planning metadata variables before template rendering."""
        engine = DocExecuteEngine(enable_tracing=False)
        engine.context = {
            "current_task": "Plan a multi-step data migration"
        }

        task = Task(
            task_id="plan_task",
            description="Plan migration",
            sop_doc_id="general/plan",
            tool={
                "tool_id": "LLM",
                "parameters": {
                    "prompt": (
                        "Plan: {task_description}\n"
                        "{available_tool_docs_xml}\n"
                        "{vector_tool_suggestions_xml}"
                    )
                }
            },
            input_json_path={"task_description": "$.current_task"},
            output_json_path="$.plan_output",
            output_description="Planning result",
            skip_new_task_generation=True,
            requires_planning_metadata=True
        )

        planning_metadata = {
            "available_tools_markdown": "Available tools (SOP references):\n<tool>\n  <tool_id>tools/python</tool_id>\n  <tool_description>Python executor</tool_description>\n</tool>",
            "vector_candidates_markdown": "Vector-recommended tools:\n<tool>\n  <tool_id>custom/doc</tool_id>\n  <tool_description>Custom doc</tool_description>\n</tool>",
            "available_tools_json": '[{"doc_id":"tools/python"}]',
            "vector_candidates_json": '[{"doc_id":"custom/doc"}]'
        }

        engine.sop_parser.get_planning_metadata = AsyncMock(return_value=planning_metadata)
        engine.sop_loader.load_sop_document = MagicMock(return_value=MagicMock(body=""))
        engine.tools["LLM"].execute = AsyncMock(return_value={"content": "ok"})

        mock_compaction.return_value = False

        asyncio.run(engine.execute_task(task))

        engine.sop_parser.get_planning_metadata.assert_awaited_once()
        called_params = engine.tools["LLM"].execute.await_args.args[0]
        self.assertIn("<tool_id>tools/python</tool_id>", called_params["prompt"])
        self.assertIn("<tool_id>custom/doc</tool_id>", called_params["prompt"])
        mock_parse_new_tasks.assert_not_awaited()


if __name__ == '__main__':
    unittest.main()
