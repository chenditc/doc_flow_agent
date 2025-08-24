#!/usr/bin/env python3
"""
Test cases for JsonPathGenerator
"""

import unittest
import sys
import os
import json
import asyncio
from unittest.mock import patch, AsyncMock, MagicMock

# Add parent directories to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from tools.json_path_generator import JsonPathGenerator
from exceptions import TaskInputMissingError


class TestJsonPathGenerator(unittest.TestCase):
    """Test cases for JsonPathGenerator class"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.generator = JsonPathGenerator()
    
    def test_init(self):
        """Test JsonPathGenerator initialization"""
        self.assertIsNotNone(self.generator.llm_tool)
    
    def test_generate_context_schema_empty(self):
        """Test context schema generation with empty context"""
        context = {}
        result = self.generator._generate_context_schema(context)
        expected = "Empty context - no data stored yet"
        self.assertEqual(result, expected)
    
    def test_generate_context_schema_simple(self):
        """Test context schema generation with simple context"""
        context = {
            "name": "John",
            "age": 25,
            "active": True
        }
        result = self.generator._generate_context_schema(context)
        
        # Should be valid JSON
        schema = json.loads(result)
        self.assertIn("name", schema)
        self.assertIn("age", schema)
        self.assertIn("active", schema)
    
    def test_generate_context_schema_excludes_temp_inputs(self):
        """Test that temporary input fields are excluded from schema"""
        context = {
            "name": "John",
            "_temp_input_123": "temporary data",
            "_temp_input_456": "more temp data",
            "age": 25
        }
        result = self.generator._generate_context_schema(context)
        
        # Should be valid JSON and exclude temp inputs
        schema = json.loads(result)
        self.assertIn("name", schema)
        self.assertIn("age", schema)
        self.assertNotIn("_temp_input_123", schema)
        self.assertNotIn("_temp_input_456", schema)
    
    def test_generate_context_schema_nested_objects(self):
        """Test context schema generation with nested objects"""
        context = {
            "user": {
                "name": "John",
                "contact": {
                    "email": "john@example.com"
                }
            },
            "settings": ["option1", "option2"]
        }
        result = self.generator._generate_context_schema(context)
        
        # Should be valid JSON
        schema = json.loads(result)
        self.assertIn("user", schema)
        self.assertIn("settings", schema)
    
    def test_cleanup_temp_inputs(self):
        """Test cleanup of temporary input fields"""
        context = {
            "name": "John",
            "_temp_input_123": "temporary data",
            "_temp_input_456": "more temp data",
            "age": 25,
            "regular_field": "keep this"
        }
        
        self.generator.cleanup_temp_inputs(context)
        
        # Temp inputs should be removed
        self.assertNotIn("_temp_input_123", context)
        self.assertNotIn("_temp_input_456", context)
        
        # Regular fields should remain
        self.assertIn("name", context)
        self.assertIn("age", context)
        self.assertIn("regular_field", context)
    
    def test_cleanup_temp_inputs_no_temp_fields(self):
        """Test cleanup when no temporary fields exist"""
        context = {
            "name": "John",
            "age": 25
        }
        original_context = context.copy()
        
        self.generator.cleanup_temp_inputs(context)
        
        # Context should remain unchanged
        self.assertEqual(context, original_context)
    
    def test_execute_extraction_code_simple(self):
        """Test execution of simple extraction code"""
        code = '''
def extract_func(context):
    return context.get('name', 'Unknown')
'''
        context = {"name": "John", "age": 25}
        
        result = self.generator._execute_extraction_code(code, context)
        self.assertEqual(result, "John")
    
    def test_execute_extraction_code_missing_field(self):
        """Test execution when field is missing"""
        code = '''
def extract_func(context):
    return context.get('missing_field')
'''
        context = {"name": "John"}
        
        result = self.generator._execute_extraction_code(code, context)
        self.assertIsNone(result)
    
    def test_execute_extraction_code_transformation(self):
        """Test execution with data transformation"""
        code = '''
def extract_func(context):
    name = context.get('first_name', '')
    surname = context.get('last_name', '')
    return f"{name} {surname}".strip()
'''
        context = {"first_name": "John", "last_name": "Doe"}
        
        result = self.generator._execute_extraction_code(code, context)
        self.assertEqual(result, "John Doe")
    
    def test_execute_extraction_code_invalid_syntax(self):
        """Test execution with invalid Python syntax"""
        code = '''
def extract_func(context):
    return context.get('name'  # Missing closing parenthesis
'''
        context = {"name": "John"}
        
        with self.assertRaises(SyntaxError):
            self.generator._execute_extraction_code(code, context)
    
    def test_execute_extraction_code_runtime_error(self):
        """Test execution with runtime error"""
        code = '''
def extract_func(context):
    return 1 / 0  # Division by zero
'''
        context = {"name": "John"}
        
        with self.assertRaises(ZeroDivisionError):
            self.generator._execute_extraction_code(code, context)
    
    def test_execute_extraction_code_missing_function(self):
        """Test execution when extract_func is not defined"""
        code = '''
def wrong_function_name(context):
    return "test"
'''
        context = {"name": "John"}
        
        # Since there's only one function, it should use that function regardless of name
        result = self.generator._execute_extraction_code(code, context)
        self.assertEqual(result, "test")
    
    def test_execute_extraction_code_not_found_pattern(self):
        """Test execution with NOT_FOUND_IN_CANDIDATES return value"""
        code = '''
def extract_func(context):
    return "<NOT_FOUND_IN_CANDIDATES>"
'''
        context = {"name": "John"}
        
        result = self.generator._execute_extraction_code(code, context)
        self.assertEqual(result, "<NOT_FOUND_IN_CANDIDATES>")
    
    @patch('builtins.print')
    def test_execute_extraction_code_prints_errors(self, mock_print):
        """Test that extraction code errors are printed"""
        code = '''
def extract_func(context):
    raise ValueError("Test error")
'''
        context = {"name": "John"}
        
        with self.assertRaises(ValueError):
            self.generator._execute_extraction_code(code, context)
        
        # Should print error message
        mock_print.assert_called()
        error_call = [call for call in mock_print.call_args_list if "Error executing extraction code" in str(call)]
        self.assertTrue(len(error_call) > 0)
    
    @patch('tools.json_path_generator.JsonPathGenerator._generate_extraction_code')
    @patch('tools.json_path_generator.JsonPathGenerator._analyze_context_candidates')
    @patch('builtins.print')
    def test_generate_input_json_paths_empty_descriptions(self, mock_print, mock_candidates, mock_extraction):
        """Test generate_input_json_paths with empty input descriptions"""
        async def run_test():
            result = await self.generator.generate_input_json_paths({}, {})
            return result
        
        result = asyncio.run(run_test())
        self.assertEqual(result, {})
        
        # Should not call analysis methods
        mock_candidates.assert_not_called()
        mock_extraction.assert_not_called()
    
    @patch('tools.json_path_generator.JsonPathGenerator._execute_extraction_code')
    @patch('tools.json_path_generator.JsonPathGenerator._generate_extraction_code')
    @patch('tools.json_path_generator.JsonPathGenerator._analyze_context_candidates')
    @patch('builtins.print')
    def test_generate_input_json_paths_success(self, mock_print, mock_candidates, mock_extraction, mock_execute):
        """Test successful input JSON path generation"""
        # Setup mocks
        mock_candidates.return_value = {"$.current_task": "test task"}
        mock_extraction.return_value = "def extract_func(context): return 'extracted_value'"
        mock_execute.return_value = "extracted_value"
        
        async def run_test():
            input_descriptions = {"field1": "Test field description"}
            context = {"current_task": "test task"}
            result = await self.generator.generate_input_json_paths(input_descriptions, context)
            return result, context
        
        result, updated_context = asyncio.run(run_test())
        
        # Should return path pointing to temporary key
        self.assertEqual(len(result), 1)
        self.assertIn("field1", result)
        self.assertTrue(result["field1"].startswith("$.["))
        self.assertTrue("_temp_input_" in result["field1"])
        
        # Context should contain temporary field
        temp_keys = [key for key in updated_context.keys() if key.startswith("_temp_input_")]
        self.assertEqual(len(temp_keys), 1)
        self.assertEqual(updated_context[temp_keys[0]], "extracted_value")
    
    @patch('tools.json_path_generator.JsonPathGenerator._execute_extraction_code')
    @patch('tools.json_path_generator.JsonPathGenerator._generate_extraction_code')
    @patch('tools.json_path_generator.JsonPathGenerator._analyze_context_candidates')
    @patch('builtins.print')
    def test_generate_input_json_paths_missing_input_error(self, mock_print, mock_candidates, mock_extraction, mock_execute):
        """Test TaskInputMissingError when extraction fails"""
        # Setup mocks
        mock_candidates.return_value = {"$.current_task": "test task"}
        mock_extraction.return_value = "def extract_func(context): return 'some code'"
        mock_execute.return_value = "<NOT_FOUND_IN_CANDIDATES>"
        
        async def run_test():
            input_descriptions = {"field1": "Test field description"}
            context = {"current_task": "test task"}
            with self.assertRaises(TaskInputMissingError) as context_manager:
                await self.generator.generate_input_json_paths(input_descriptions, context)
            return str(context_manager.exception)
        
        error_message = asyncio.run(run_test())
        self.assertIn("field1", error_message)
        self.assertIn("Test field description", error_message)
    
    @patch.object(JsonPathGenerator, '_create_output_path_prompt')
    @patch('builtins.print')
    def test_generate_output_json_path_empty_description(self, mock_print, mock_prompt):
        """Test generate_output_json_path with empty description"""
        async def run_test():
            with self.assertRaises(ValueError) as context:
                await self.generator.generate_output_json_path("", {})
            return str(context.exception)
        
        error_message = asyncio.run(run_test())
        self.assertEqual(error_message, "Output description cannot be empty")
        
        # Should not call prompt creation
        mock_prompt.assert_not_called()
    
    @patch('tools.llm_tool.LLMTool.execute')
    @patch('builtins.print')
    def test_generate_output_json_path_json_response(self, mock_print, mock_llm_execute):
        """Test generate_output_json_path with valid JSON response"""
        # Mock LLM response with JSON
        mock_llm_execute.return_value = {"content": '{"output_path": "$.results.data"}', "tool_calls": []}
        
        async def run_test():
            result = await self.generator.generate_output_json_path(
                "test output description",
                {"existing": "data"}
            )
            return result
        
        result = asyncio.run(run_test())
        self.assertEqual(result, "$.results.data")
    
    @patch('tools.llm_tool.LLMTool.execute')
    @patch('builtins.print')
    def test_generate_output_json_path_text_response(self, mock_print, mock_llm_execute):
        """Test generate_output_json_path with text response containing path"""
        # Mock LLM response with plain text path
        mock_llm_execute.return_value = {"content": '$.custom.path', "tool_calls": []}
        
        async def run_test():
            result = await self.generator.generate_output_json_path(
                "test output description",
                {"existing": "data"}
            )
            return result
        
        result = asyncio.run(run_test())
        self.assertEqual(result, "$.custom.path")
    
    @patch('tools.llm_tool.LLMTool.execute')
    @patch('builtins.print')
    def test_generate_output_json_path_invalid_response(self, mock_print, mock_llm_execute):
        """Test generate_output_json_path with invalid response"""
        # Mock LLM response that's neither valid JSON nor a path
        mock_llm_execute.return_value = {"content": 'invalid response', "tool_calls": []}
        
        async def run_test():
            result = await self.generator.generate_output_json_path(
                "test output description",
                {"existing": "data"}
            )
            return result
        
        # Should raise and ValueError
        with self.assertRaises(ValueError) as context:
            result = asyncio.run(run_test())
        self.assertIn("Invalid output path format for output json path extraction", str(context.exception))


if __name__ == '__main__':
    unittest.main()
