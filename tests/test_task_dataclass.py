#!/usr/bin/env python3
"""
Unit tests for Task dataclass from doc_execute_engine.py
"""

import unittest
import json
from dataclasses import asdict

from doc_execute_engine import Task


class TestTaskDataclass(unittest.TestCase):
    """Test Task dataclass creation and string formatting"""

    def setUp(self):
        """Set up test fixtures"""
        self.sample_task_data = {
            "task_id": "test-task-001",
            "description": "Test task description",
            "sop_doc_id": "test/document",
            "tool": {
                "tool_id": "LLM",
                "parameters": {
                    "prompt": "Test prompt",
                    "temperature": 0.7
                }
            },
            "input_json_path": {
                "input1": "$.user.name",
                "input2": "$.user.email"
            },
            "output_json_path": "$.result.output",
            "output_description": "Test output description"
        }

    def test_task_creation_with_all_fields(self):
        """Test creating a Task instance with all fields"""
        task = Task(**self.sample_task_data)
        
        self.assertEqual(task.task_id, "test-task-001")
        self.assertEqual(task.description, "Test task description")
        self.assertEqual(task.sop_doc_id, "test/document")
        self.assertEqual(task.tool["tool_id"], "LLM")
        self.assertEqual(task.tool["parameters"]["prompt"], "Test prompt")
        self.assertEqual(task.tool["parameters"]["temperature"], 0.7)
        self.assertEqual(task.input_json_path["input1"], "$.user.name")
        self.assertEqual(task.input_json_path["input2"], "$.user.email")
        self.assertEqual(task.output_json_path, "$.result.output")
        self.assertEqual(task.output_description, "Test output description")

    def test_task_creation_without_optional_fields(self):
        """Test creating a Task instance without optional fields"""
        minimal_data = {
            "task_id": "minimal-task",
            "description": "Minimal task",
            "sop_doc_id": "minimal/doc",
            "tool": {"tool_id": "CLI"},
            "input_json_path": {"input": "$.data"},
            "output_json_path": "$.output"
        }
        
        task = Task(**minimal_data)
        
        self.assertEqual(task.task_id, "minimal-task")
        self.assertEqual(task.description, "Minimal task")
        self.assertEqual(task.sop_doc_id, "minimal/doc")
        self.assertEqual(task.tool["tool_id"], "CLI")
        self.assertEqual(task.input_json_path["input"], "$.data")
        self.assertEqual(task.output_json_path, "$.output")
        self.assertIsNone(task.output_description)

    def test_task_str_method(self):
        """Test Task __str__ method formatting"""
        task = Task(**self.sample_task_data)
        task_str = str(task)
        
        # Check that all required fields are in the string representation
        self.assertIn("Task ID: test-task-001", task_str)
        self.assertIn("Description: Test task description", task_str)
        self.assertIn("SOP Document ID: test/document", task_str)
        self.assertIn("Tool: LLM", task_str)
        self.assertIn("Input JSON Paths:", task_str)
        self.assertIn("Output JSON Path: $.result.output", task_str)
        self.assertIn("Output Description: Test output description", task_str)
        
        # Check that JSON is properly formatted in the string
        self.assertIn('"input1": "$.user.name"', task_str)
        self.assertIn('"input2": "$.user.email"', task_str)

    def test_task_str_method_with_missing_tool_id(self):
        """Test Task __str__ method when tool doesn't have tool_id"""
        data_without_tool_id = self.sample_task_data.copy()
        data_without_tool_id["tool"] = {"parameters": {"test": "value"}}
        
        task = Task(**data_without_tool_id)
        task_str = str(task)
        
        # Should show 'N/A' when tool_id is missing
        self.assertIn("Tool: N/A", task_str)

    def test_task_repr_method(self):
        """Test Task __repr__ method formatting"""
        task = Task(**self.sample_task_data)
        task_repr = repr(task)
        
        # Check that repr contains the expected format
        self.assertTrue(task_repr.startswith("Task("))
        self.assertIn("task_id=test-task-001", task_repr)
        self.assertIn("description=Test task description", task_repr)
        self.assertIn("sop_doc_id=test/document", task_repr)
        self.assertIn("tool=LLM", task_repr)
        self.assertIn("output_json_path=$.result.output", task_repr)
        self.assertIn("output_description=Test output description", task_repr)

    def test_task_repr_method_with_missing_tool_id(self):
        """Test Task __repr__ method when tool doesn't have tool_id"""
        data_without_tool_id = self.sample_task_data.copy()
        data_without_tool_id["tool"] = {"parameters": {"test": "value"}}
        
        task = Task(**data_without_tool_id)
        task_repr = repr(task)
        
        # Should show 'N/A' when tool_id is missing
        self.assertIn("tool=N/A", task_repr)

    def test_task_dataclass_fields(self):
        """Test that Task is properly defined as a dataclass"""
        task = Task(**self.sample_task_data)
        
        # Test that asdict works (confirms it's a proper dataclass)
        task_dict = asdict(task)
        
        self.assertEqual(task_dict["task_id"], "test-task-001")
        self.assertEqual(task_dict["description"], "Test task description")
        self.assertEqual(task_dict["sop_doc_id"], "test/document")
        self.assertEqual(task_dict["tool"]["tool_id"], "LLM")
        self.assertEqual(task_dict["input_json_path"]["input1"], "$.user.name")
        self.assertEqual(task_dict["output_json_path"], "$.result.output")
        self.assertEqual(task_dict["output_description"], "Test output description")

    def test_task_with_empty_input_json_path(self):
        """Test Task with empty input_json_path"""
        data = self.sample_task_data.copy()
        data["input_json_path"] = {}
        
        task = Task(**data)
        task_str = str(task)
        
        self.assertEqual(task.input_json_path, {})
        self.assertIn("Input JSON Paths: {}", task_str)

    def test_task_with_complex_tool_structure(self):
        """Test Task with complex tool structure"""
        data = self.sample_task_data.copy()
        data["tool"] = {
            "tool_id": "UserCommunicate",
            "parameters": {
                "message": "Please provide input",
                "options": ["option1", "option2"],
                "timeout": 300
            },
            "metadata": {
                "version": "1.0",
                "author": "test"
            }
        }
        
        task = Task(**data)
        
        self.assertEqual(task.tool["tool_id"], "UserCommunicate")
        self.assertEqual(task.tool["parameters"]["message"], "Please provide input")
        self.assertEqual(task.tool["parameters"]["options"], ["option1", "option2"])
        self.assertEqual(task.tool["metadata"]["version"], "1.0")
        
        # Test string representation
        task_str = str(task)
        self.assertIn("Tool: UserCommunicate", task_str)

    def test_task_with_unicode_content(self):
        """Test Task with unicode characters in various fields"""
        unicode_data = {
            "task_id": "unicode-task-测试",
            "description": "Unicode description with 中文 characters",
            "sop_doc_id": "unicode/文档",
            "tool": {"tool_id": "LLM", "parameters": {"prompt": "测试提示"}},
            "input_json_path": {"用户输入": "$.用户.姓名"},
            "output_json_path": "$.结果.输出",
            "output_description": "Unicode output 描述"
        }
        
        task = Task(**unicode_data)
        
        self.assertEqual(task.task_id, "unicode-task-测试")
        self.assertEqual(task.description, "Unicode description with 中文 characters")
        self.assertEqual(task.input_json_path["用户输入"], "$.用户.姓名")
        
        # Test that string representation handles unicode properly
        task_str = str(task)
        self.assertIn("unicode-task-测试", task_str)
        self.assertIn("中文", task_str)
        self.assertIn("用户输入", task_str)


if __name__ == "__main__":
    unittest.main()
