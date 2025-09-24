#!/usr/bin/env python3
"""
Test cases for SmartJsonPathGenerator
"""

import unittest
import sys
import os
import json
import asyncio
from unittest.mock import patch, AsyncMock, MagicMock

# Add parent directories to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from tools.json_path_generator import SmartJsonPathGenerator
from exceptions import TaskInputMissingError


class TestJsonPathGenerator(unittest.TestCase):
    """Test cases for SmartJsonPathGenerator class"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.generator = SmartJsonPathGenerator()
    
    def test_init(self):
        """Test SmartJsonPathGenerator initialization"""
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
    
    @patch('tools.json_path_generator.OnebyOneJsonPathGenerator._generate_extraction_code')
    @patch('tools.json_path_generator.SmartJsonPathGenerator._analyze_context_candidates')
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
    
    @patch('tools.json_path_generator.OnebyOneJsonPathGenerator._execute_extraction_code')
    @patch('tools.json_path_generator.OnebyOneJsonPathGenerator._generate_extraction_code')
    @patch('tools.json_path_generator.OnebyOneJsonPathGenerator._analyze_context_candidates')
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
    
    @patch('tools.json_path_generator.OnebyOneJsonPathGenerator._execute_extraction_code')
    @patch('tools.json_path_generator.OnebyOneJsonPathGenerator._generate_extraction_code')
    @patch('tools.json_path_generator.OnebyOneJsonPathGenerator._analyze_context_candidates')
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
    
    @patch.object(SmartJsonPathGenerator, '_create_output_path_prompt')
    @patch('builtins.print')
    def test_generate_output_json_path_empty_description(self, mock_print, mock_prompt):
        """Test generate_output_json_path with empty description"""
        async def run_test():
            with self.assertRaises(ValueError) as context:
                await self.generator.generate_output_json_path("", "out", {})
            return str(context.exception)
        
        error_message = asyncio.run(run_test())
        self.assertEqual(error_message, "Output description cannot be empty")
        
        # Should not call prompt creation
        mock_prompt.assert_not_called()
    
    @patch('tools.llm_tool.LLMTool.execute')
    @patch('builtins.print')
    def test_generate_output_json_path_json_response(self, mock_print, mock_llm_execute):
        """Test generate_output_json_path with tool call response (no longer supports JSON fallback)"""
        # Mock LLM response with tool call (updated to use tool calls instead of JSON fallback)
        mock_llm_execute.return_value = {
            "content": "I'll generate the path using the tool", 
            "tool_calls": [{
                "name": "generate_output_path",
                "arguments": {"output_path": "$.results.data"}
            }]
        }
        
        async def run_test():
            result = await self.generator.generate_output_json_path(
                "test output description",
                "test_output",
                {"existing": "data"}
            )
            return result
        
        result = asyncio.run(run_test())
        self.assertEqual(result, "$.results.data")
    
    @patch('tools.llm_tool.LLMTool.execute')
    @patch('builtins.print')
    def test_generate_output_json_path_text_response(self, mock_print, mock_llm_execute):
        """Test generate_output_json_path with tool call response (no longer supports text fallback)"""
        # Mock LLM response with tool call (updated to use tool calls instead of text fallback)
        mock_llm_execute.return_value = {
            "content": "I'll generate the custom path using the tool", 
            "tool_calls": [{
                "name": "generate_output_path", 
                "arguments": {"output_path": "$.custom.path"}
            }]
        }
        
        async def run_test():
            result = await self.generator.generate_output_json_path(
                "test output description",
                "test_output",
                {"existing": "data"}
            )
            return result
        
        result = asyncio.run(run_test())
        self.assertEqual(result, "$.custom.path")
    
    @patch('tools.llm_tool.LLMTool.execute')
    @patch('builtins.print')
    def test_generate_output_json_path_no_tool_calls(self, mock_print, mock_llm_execute):
        """Test generate_output_json_path when LLM doesn't return tool calls"""
        # Mock LLM response without tool calls (should raise error)
        mock_llm_execute.return_value = {"content": 'some response', "tool_calls": []}
        
        async def run_test():
            result = await self.generator.generate_output_json_path(
                "test output description",
                "test_output",
                {"existing": "data"}
            )
            return result
        
        # Should raise ValueError when no tool calls are returned
        with self.assertRaises(ValueError) as context:
            result = asyncio.run(run_test())
        self.assertIn("LLM did not return any tool calls for output path generation", str(context.exception))
    
    @patch('tools.llm_tool.LLMTool.execute')
    @patch('builtins.print')
    def test_generate_output_json_path_missing_arguments(self, mock_print, mock_llm_execute):
        """Test generate_output_json_path when tool call is missing required arguments"""
        # Mock LLM response with tool call but missing arguments
        mock_llm_execute.return_value = {
            "content": 'I forgot to include the path',
            "tool_calls": [{
                "name": "generate_output_path",
                "arguments": {}  # Missing output_path
            }]
        }
        
        async def run_test():
            result = await self.generator.generate_output_json_path(
                "test output description",
                "test_output",
                {"existing": "data"}
            )
            return result
        
        # Should use default fallback path when argument is missing
        result = asyncio.run(run_test())
        self.assertEqual(result, "$.output")

    @patch('tools.llm_tool.LLMTool.execute')
    @patch('builtins.print')
    def test_generate_output_json_path_with_tool_call(self, mock_print, mock_llm_execute):
        """Test generate_output_json_path with tool call response"""
        # Mock LLM response with tool call
        mock_llm_execute.return_value = {
            "content": "I'll generate the appropriate output path",
            "tool_calls": [{
                "name": "generate_output_path",
                "arguments": {"output_path": "$.generated_blog_outline"}
            }]
        }
        
        async def run_test():
            result = await self.generator.generate_output_json_path(
                "Blog outline generated based on title",
                "blog_outline",
                {"current_task": "Generate a blog outline"}
            )
            return result
        
        result = asyncio.run(run_test())
        self.assertEqual(result, "$.generated_blog_outline")
        
        # Verify that LLM was called with tools parameter
        mock_llm_execute.assert_called_once()
        call_args = mock_llm_execute.call_args[0][0]
        self.assertIn("tools", call_args)
        self.assertEqual(len(call_args["tools"]), 1)
        self.assertEqual(call_args["tools"][0]["function"]["name"], "generate_output_path")

    @patch('tools.llm_tool.LLMTool.execute')
    @patch('builtins.print')
    def test_generate_output_json_path_wrong_tool_call(self, mock_print, mock_llm_execute):
        """Test generate_output_json_path with wrong tool call name"""
        # Mock LLM response with wrong tool call
        mock_llm_execute.return_value = {
            "content": "I'll use a different tool",
            "tool_calls": [{
                "name": "wrong_tool_name",
                "arguments": {"output_path": "$.some_path"}
            }]
        }
        
        async def run_test():
            result = await self.generator.generate_output_json_path(
                "test description",
                "test_output",
                {"existing": "data"}
            )
            return result
        
        # Should raise ValueError
        with self.assertRaises(ValueError) as context:
            result = asyncio.run(run_test())
        self.assertIn("Unexpected tool call: wrong_tool_name", str(context.exception))

    def test_create_output_path_tool_schema(self):
        """Test _create_output_path_tool_schema method"""
        schema = self.generator._create_output_path_tool_schema()
        
        # Verify schema structure
        self.assertIn("type", schema)
        self.assertEqual(schema["type"], "function")
        self.assertIn("function", schema)
        
        function_def = schema["function"]
        self.assertEqual(function_def["name"], "generate_output_path")
        self.assertIn("description", function_def)
        self.assertIn("parameters", function_def)
        
        parameters = function_def["parameters"]
        self.assertEqual(parameters["type"], "object")
        self.assertIn("properties", parameters)
        self.assertIn("required", parameters)
        
        properties = parameters["properties"]
        self.assertIn("output_path", properties)
        self.assertEqual(properties["output_path"]["type"], "string")
        self.assertIn("description", properties["output_path"])
        
        self.assertEqual(parameters["required"], ["output_path"])


class TestBatchJsonPathGenerator(unittest.TestCase):
    """Test cases for BatchJsonPathGenerator class"""
    
    def setUp(self):
        """Set up test fixtures"""
        from tools.json_path_generator import BatchJsonPathGenerator
        
        # Create mock LLM tool
        self.mock_llm_tool = AsyncMock()
        self.mock_tracer = MagicMock()
        
        self.generator = BatchJsonPathGenerator(
            llm_tool=self.mock_llm_tool,
            tracer=self.mock_tracer
        )
    
    def test_inheritance(self):
        """Test that BatchJsonPathGenerator properly inherits from BaseJsonPathGenerator"""
        from tools.json_path_generator import BaseJsonPathGenerator, BatchJsonPathGenerator
        
        generator = BatchJsonPathGenerator()
        self.assertIsInstance(generator, BaseJsonPathGenerator)
    
    def test_create_extraction_tool_schema(self):
        """Test tool schema creation for extraction"""
        input_descriptions = {
            "title": "The title of the blog",
            "topic": "The main topic",
            "user_request": "What the user wants"
        }
        
        schema = self.generator._create_extraction_tool_schema(input_descriptions)
        
        # Verify schema structure
        self.assertEqual(schema["type"], "function")
        self.assertEqual(schema["function"]["name"], "extract_request_parameters")
        self.assertIn("description", schema["function"])
        
        parameters = schema["function"]["parameters"]
        self.assertEqual(parameters["type"], "object")
        self.assertIn("properties", parameters)
        self.assertIn("required", parameters)
        
        # Verify all fields are included
        properties = parameters["properties"]
        required = parameters["required"]
        
        for field_name, description in input_descriptions.items():
            self.assertIn(field_name, properties)
            self.assertIn(field_name, required)
            self.assertEqual(properties[field_name]["type"], "string")
            self.assertIn(description, properties[field_name]["description"])
    
    def test_create_extraction_tool_schema_empty(self):
        """Test tool schema creation with empty input descriptions"""
        input_descriptions = {}
        
        schema = self.generator._create_extraction_tool_schema(input_descriptions)
        
        parameters = schema["function"]["parameters"]
        self.assertEqual(len(parameters["properties"]), 0)
        self.assertEqual(len(parameters["required"]), 0)
    
    @patch('tools.json_path_generator.BatchJsonPathGenerator._analyze_context_candidates')
    def test_extract_all_fields_with_llm_success(self, mock_analyze):
        """Test successful field extraction with LLM"""
        # Setup
        input_descriptions = {
            "title": "Blog title",
            "topic": "Main topic"
        }
        candidate_fields = {
            "$.current_task": "Generate blog about AI",
            "$.user_purpose": "Learning"
        }
        context = {"current_task": "Generate blog about AI"}
        user_ask = "Create AI blog"
        
        # Mock LLM response
        self.mock_llm_tool.execute.return_value = {
            "content": "Extraction completed",
            "tool_calls": [
                {
                    "name": "extract_request_parameters",
                    "arguments": {
                        "title": "AI Blog Title",
                        "topic": "Artificial Intelligence"
                    }
                }
            ]
        }
        
        # Create tool schema
        tool_schema = self.generator._create_extraction_tool_schema(input_descriptions)
        
        async def run_test():
            return await self.generator._extract_all_fields_with_llm(
                input_descriptions, candidate_fields, user_ask, tool_schema
            )
        
        # Execute
        result = asyncio.run(run_test())
        
        # Verify
        self.assertEqual(result["title"], "AI Blog Title")
        self.assertEqual(result["topic"], "Artificial Intelligence")
        
        # Verify LLM was called with correct parameters
        self.mock_llm_tool.execute.assert_called_once()
        call_args = self.mock_llm_tool.execute.call_args[0][0]
        self.assertIn("prompt", call_args)
        self.assertIn("tools", call_args)
        self.assertEqual(len(call_args["tools"]), 1)
    
    @patch('tools.json_path_generator.BatchJsonPathGenerator._analyze_context_candidates')
    def test_extract_all_fields_with_llm_no_tool_calls(self, mock_analyze):
        """Test LLM response with no tool calls"""
        input_descriptions = {"title": "Blog title"}
        candidate_fields = {}
        context = {}
        user_ask = "test"
        tool_schema = self.generator._create_extraction_tool_schema(input_descriptions)
        
        # Mock LLM response without tool calls
        self.mock_llm_tool.execute.return_value = {
            "content": "No extraction possible",
            "tool_calls": []
        }
        
        async def run_test():
            return await self.generator._extract_all_fields_with_llm(
                input_descriptions, candidate_fields, user_ask, tool_schema
            )
        
        result = asyncio.run(run_test())
        
        # Should return NOT_FOUND for all fields
        self.assertEqual(result["title"], "<NOT_FOUND_IN_CANDIDATES>")
    
    @patch('tools.json_path_generator.BatchJsonPathGenerator._analyze_context_candidates')
    def test_extract_all_fields_with_llm_wrong_tool_call(self, mock_analyze):
        """Test LLM response with wrong tool call name"""
        input_descriptions = {"title": "Blog title"}
        candidate_fields = {}
        context = {}
        user_ask = "test"
        tool_schema = self.generator._create_extraction_tool_schema(input_descriptions)
        
        # Mock LLM response with wrong tool call
        self.mock_llm_tool.execute.return_value = {
            "content": "Wrong tool call",
            "tool_calls": [
                {
                    "name": "wrong_function_name",
                    "arguments": {"title": "Test"}
                }
            ]
        }
        
        async def run_test():
            return await self.generator._extract_all_fields_with_llm(
                input_descriptions, candidate_fields, user_ask, tool_schema
            )
        
        # Should raise ValueError
        with self.assertRaises(ValueError) as context:
            result = asyncio.run(run_test())
        self.assertIn("Unexpected tool call", str(context.exception))
    
    @patch('tools.json_path_generator.BatchJsonPathGenerator._analyze_context_candidates')
    @patch('tools.json_path_generator.BatchJsonPathGenerator._extract_all_fields_with_llm')
    def test_generate_input_json_paths_success(self, mock_extract, mock_analyze):
        """Test successful input path generation"""
        # Setup
        input_descriptions = {
            "title": "Blog title",
            "topic": "Main topic"
        }
        context = {"current_task": "Generate AI blog"}
        user_ask = "Create blog"
        
        # Mock dependencies
        mock_analyze.return_value = {"$.current_task": "Generate AI blog"}
        mock_extract.return_value = {
            "title": "AI in 2024",
            "topic": "Artificial Intelligence"
        }
        
        async def run_test():
            return await self.generator.generate_input_json_paths(
                input_descriptions, context, user_ask
            )
        
        result = asyncio.run(run_test())
        
        # Verify paths were generated
        self.assertEqual(len(result), 2)
        self.assertIn("title", result)
        self.assertIn("topic", result)
        
        # Verify paths have correct format
        for field_name, path in result.items():
            self.assertTrue(path.startswith("$."))
            self.assertIn("_temp_input_", path)
        
        # Verify temp values were added to context
        temp_keys = [key for key in context.keys() if key.startswith("_temp_input_")]
        self.assertEqual(len(temp_keys), 2)
    
    @patch('tools.json_path_generator.BatchJsonPathGenerator._analyze_context_candidates')
    @patch('tools.json_path_generator.BatchJsonPathGenerator._extract_all_fields_with_llm')
    def test_generate_input_json_paths_missing_field(self, mock_extract, mock_analyze):
        """Test input path generation with missing field"""
        # Setup
        input_descriptions = {"title": "Blog title"}
        test_context = {}
        user_ask = "test"
        
        # Mock missing field
        mock_analyze.return_value = {}
        mock_extract.return_value = {"title": "<NOT_FOUND_IN_CANDIDATES>"}
        
        async def run_test():
            return await self.generator.generate_input_json_paths(
                input_descriptions, test_context, user_ask
            )
        
        # Should raise TaskInputMissingError
        with self.assertRaises(TaskInputMissingError) as ctx:
            result = asyncio.run(run_test())
    
    def test_generate_input_json_paths_empty(self):
        """Test input path generation with empty descriptions"""
        async def run_test():
            return await self.generator.generate_input_json_paths(
                {}, {}, ""
            )
        
        result = asyncio.run(run_test())
        self.assertEqual(result, {})
    
    @patch('tools.json_path_generator.BatchJsonPathGenerator._analyze_context_candidates')
    @patch('tools.json_path_generator.BatchJsonPathGenerator._extract_all_fields_with_llm')
    def test_generate_input_json_paths_ensures_current_task(self, mock_extract, mock_analyze):
        """Test that current_task is always included in candidates"""
        input_descriptions = {"title": "Blog title"}
        context = {"current_task": "Generate blog", "other_field": "value"}
        user_ask = "test"
        
        # Mock that analyze doesn't return current_task
        mock_analyze.return_value = {"$.other_field": "value"}
        mock_extract.return_value = {"title": "Test Title"}
        
        async def run_test():
            return await self.generator.generate_input_json_paths(
                input_descriptions, context, user_ask
            )
        
        result = asyncio.run(run_test())
        
        # Verify extract was called with current_task included
        call_args = mock_extract.call_args[0]
        candidate_fields = call_args[1]  # second argument
        self.assertIn("current_task", candidate_fields)
        self.assertEqual(candidate_fields["current_task"], "Generate blog")


if __name__ == '__main__':
    unittest.main()
