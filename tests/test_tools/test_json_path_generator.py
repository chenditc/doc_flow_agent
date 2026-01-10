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

from tools.json_path_generator import SmartJsonPathGenerator, BaseJsonPathGenerator
from tools.llm_tool import LLMTool
from exceptions import TaskInputMissingError


class TestJsonPathGenerator(unittest.TestCase):
    """Test cases for JsonPathGenerator classes"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.llm_tool_mock = MagicMock()
        self.llm_tool_mock.execute = AsyncMock()
        self.smart_generator = SmartJsonPathGenerator(llm_tool=self.llm_tool_mock)
        self.base_generator = BaseJsonPathGenerator(llm_tool=self.llm_tool_mock)
    
    def test_init(self):
        """Test SmartJsonPathGenerator initialization"""
        self.assertIsNotNone(self.smart_generator.llm_tool)
    
    def test_generate_context_schema_empty(self):
        """Test context schema generation with empty context"""
        context = {}
        result = self.smart_generator._generate_context_schema(context)
        expected = "Empty context - no data stored yet"
        self.assertEqual(result, expected)
    
    def test_generate_context_schema_simple(self):
        """Test context schema generation with simple context"""
        context = {
            "name": "John",
            "age": 25,
            "active": True
        }
        result = self.smart_generator._generate_context_schema(context)
        
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
        result = self.smart_generator._generate_context_schema(context)
        
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
        result = self.smart_generator._generate_context_schema(context)
        
        # Should be valid JSON
        schema = json.loads(result)
        self.assertIn("user", schema)
        self.assertIn("settings", schema)

    @patch('builtins.print')
    def test_analyze_context_candidates_includes_task_short_name(self, mock_print):
        """Ensure task short name is threaded into the prompt for candidate analysis"""
        async def run_test():
            # Use at least 10 items to avoid the quick return path
            context = {f"field_{idx}": idx for idx in range(10)}
            self.smart_generator.llm_tool.execute.return_value = {"content": '["$.field_1"]'}

            await self.smart_generator._analyze_context_candidates(
                "Test description",
                context,
                "Original ask",
                task_short_name="Summarize Chapter 1"
            )

            call_args = self.smart_generator.llm_tool.execute.call_args[0][0]
            prompt = call_args["prompt"]
            self.assertIn("Summarize Chapter 1", prompt)
            self.assertIn("## Request Short Name", prompt)

        asyncio.run(run_test())
    
    def test_cleanup_temp_inputs(self):
        """Test cleanup of temporary input fields"""
        context = {
            "name": "John",
            "_temp_input_123": "temporary data",
            "_temp_input_456": "more temp data",
            "age": 25,
            "regular_field": "keep this"
        }
        
        self.smart_generator.cleanup_temp_inputs(context)
        
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
        
        self.smart_generator.cleanup_temp_inputs(context)
        
        # Context should remain unchanged
        self.assertEqual(context, original_context)
    
    def test_execute_extraction_code_simple(self):
        """Test execution of simple extraction code"""
        code = '''
def extract_func(context):
    return context.get('name', 'Unknown')
'''
        context = {"name": "John", "age": 25}
        
        result = self.smart_generator._execute_extraction_code(code, context)
        self.assertEqual(result, "John")
    
    def test_execute_extraction_code_missing_field(self):
        """Test execution when field is missing"""
        code = '''
def extract_func(context):
    return context.get('missing_field')
'''
        context = {"name": "John"}
        
        result = self.smart_generator._execute_extraction_code(code, context)
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
        
        result = self.smart_generator._execute_extraction_code(code, context)
        self.assertEqual(result, "John Doe")
    
    def test_execute_extraction_code_invalid_syntax(self):
        """Test execution with invalid Python syntax"""
        code = '''
def extract_func(context):
    return context.get('name'  # Missing closing parenthesis
'''
        context = {"name": "John"}
        
        with self.assertRaises(SyntaxError):
            self.smart_generator._execute_extraction_code(code, context)
    
    def test_execute_extraction_code_runtime_error(self):
        """Test execution with runtime error"""
        code = '''
def extract_func(context):
    return 1 / 0  # Division by zero
'''
        context = {"name": "John"}
        
        with self.assertRaises(ZeroDivisionError):
            self.smart_generator._execute_extraction_code(code, context)
    
    def test_execute_extraction_code_missing_function(self):
        """Test execution when extract_func is not defined"""
        code = '''
def wrong_function_name(context):
    return "test"
'''
        context = {"name": "John"}
        
        # Since there's only one function, it should use that function regardless of name
        result = self.smart_generator._execute_extraction_code(code, context)
        self.assertEqual(result, "test")
    
    def test_execute_extraction_code_not_found_pattern(self):
        """Test execution with NOT_FOUND_IN_CANDIDATES return value"""
        code = '''
def extract_func(context):
    return "<NOT_FOUND_IN_CANDIDATES>"
'''
        context = {"name": "John"}
        
        result = self.smart_generator._execute_extraction_code(code, context)
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
            self.smart_generator._execute_extraction_code(code, context)
        
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
            result = await self.smart_generator.generate_input_json_paths(
                {}, {}, tool_description="unit-test-tool"
            )
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
            result = await self.smart_generator.generate_input_json_paths(
                input_descriptions, context, tool_description="unit-test-tool"
            )
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
                await self.smart_generator.generate_input_json_paths(
                    input_descriptions, context, tool_description="unit-test-tool"
                )
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
                await self.smart_generator.generate_output_json_path("", "out", {})
            return str(context.exception)
        
        error_message = asyncio.run(run_test())
        self.assertEqual(error_message, "Output description cannot be empty")
        
        # Should not call prompt creation
        mock_prompt.assert_not_called()
    
    @patch('builtins.print')
    def test_generate_output_json_path_json_response(self, mock_print):
        """Test generate_output_json_path with tool call response (no longer supports JSON fallback)"""
        # Mock LLM response with tool call (updated to use tool calls instead of JSON fallback)
        self.smart_generator.llm_tool.execute.return_value = {
            "content": "I'll generate the path using the tool", 
            "tool_calls": [{
                "name": "generate_output_path",
                "arguments": {"output_path": "$.results.data"}
            }]
        }
        
        async def run_test():
            result = await self.smart_generator.generate_output_json_path(
                "test output description",
                "test_output",
                {"existing": "data"}
            )
            return result
        
        result = asyncio.run(run_test())
        self.assertEqual(result, "$.results.data")
    
    @patch('builtins.print')
    def test_generate_output_json_path_text_response(self, mock_print):
        """Test generate_output_json_path with tool call response (no longer supports text fallback)"""
        # Mock LLM response with tool call (updated to use tool calls instead of text fallback)
        self.smart_generator.llm_tool.execute.return_value = {
            "content": "I'll generate the custom path using the tool", 
            "tool_calls": [{
                "name": "generate_output_path", 
                "arguments": {"output_path": "$.custom.path"}
            }]
        }
        
        async def run_test():
            result = await self.smart_generator.generate_output_json_path(
                "test output description",
                "test_output",
                {"existing": "data"}
            )
            return result
        
        result = asyncio.run(run_test())
        self.assertEqual(result, "$.custom.path")
    
    @patch('builtins.print')
    def test_generate_output_json_path_no_tool_calls(self, mock_print):
        """Test generate_output_json_path when LLM doesn't return tool calls"""
        # Mock LLM response without tool calls (should raise error)
        self.smart_generator.llm_tool.execute.return_value = {"content": 'some response', "tool_calls": []}
        
        async def run_test():
            result = await self.smart_generator.generate_output_json_path(
                "test output description",
                "test_output",
                {"existing": "data"}
            )
            return result
        
        # Should raise ValueError when no tool calls are returned
        with self.assertRaises(ValueError) as context:
            asyncio.run(run_test())
        self.assertIn("LLM did not return any tool calls for output path generation", str(context.exception))
    
    @patch('builtins.print')
    def test_generate_output_json_path_missing_arguments(self, mock_print):
        """Test generate_output_json_path when tool call is missing required arguments"""
        # Mock LLM response with tool call but missing arguments
        self.smart_generator.llm_tool.execute.return_value = {
            "content": 'I forgot to include the path',
            "tool_calls": [{
                "name": "generate_output_path",
                "arguments": {}  # Missing output_path
            }]
        }
        
        async def run_test():
            result = await self.smart_generator.generate_output_json_path(
                "test output description",
                "test_output",
                {"existing": "data"}
            )
            return result
        
        # Should use default fallback path when argument is missing
        result = asyncio.run(run_test())
        self.assertEqual(result, "$.output")

    @patch('builtins.print')
    def test_generate_output_json_path_with_tool_call(self, mock_print):
        """Test generate_output_json_path with tool call response"""
        # Mock LLM response with tool call
        self.smart_generator.llm_tool.execute.return_value = {
            "content": "I'll generate the appropriate output path",
            "tool_calls": [{
                "name": "generate_output_path",
                "arguments": {"output_path": "$.generated_blog_outline"}
            }]
        }
        
        async def run_test():
            result = await self.smart_generator.generate_output_json_path(
                "Blog outline generated based on title",
                "blog_outline",
                {"current_task": "Generate a blog outline"}
            )
            return result
        
        result = asyncio.run(run_test())
        self.assertEqual(result, "$.generated_blog_outline")
        
        # Verify that LLM was called with tools parameter
        self.smart_generator.llm_tool.execute.assert_called_once()
        call_args = self.smart_generator.llm_tool.execute.call_args[0][0]
        self.assertIn("tools", call_args)
        self.assertEqual(len(call_args["tools"]), 1)
        self.assertEqual(call_args["tools"][0]["function"]["name"], "generate_output_path")

    @patch('builtins.print')
    def test_generate_output_json_path_wrong_tool_call(self, mock_print):
        """Test generate_output_json_path with wrong tool call name"""
        # Mock LLM response with wrong tool call
        self.smart_generator.llm_tool.execute.return_value = {
            "content": "I'll use a different tool",
            "tool_calls": [{
                "name": "wrong_tool_name",
                "arguments": {"output_path": "$.some_path"}
            }]
        }
        
        async def run_test():
            await self.smart_generator.generate_output_json_path(
                "test description",
                "test_output",
                {"existing": "data"}
            )
        
        # Should raise ValueError
        with self.assertRaises(ValueError) as context:
            asyncio.run(run_test())
        self.assertIn("Unexpected tool call: wrong_tool_name", str(context.exception))

    def test_create_output_path_tool_schema(self):
        """Test _create_output_path_tool_schema method"""
        schema = self.smart_generator._create_output_path_tool_schema()
        
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

    def test_shorten_path_key(self):
        """Test shorten_path_key method"""
        key_value_pairs = {
            "this_is_a_very_long_key_name": "value1",
            "another_super_long_key_that_needs_shortening": "value2",
            "short_key": "value3"
        }
        
        # Mock the LLM response
        self.base_generator.llm_tool.execute.return_value = {
            "tool_calls": [
                {
                    "name": "shorten_keys",
                    "arguments": {
                        "this_is_a_very_long_key_name": "short_key_1",
                        "another_super_long_key_that_needs_shortening": "short_key_2",
                        "short_key": "short_key"
                    }
                }
            ]
        }

        async def run_test():
            result = await self.base_generator.shorten_path_key(key_value_pairs)

            expected_result = {
                "short_key_1": "value1",
                "short_key_2": "value2",
                "short_key": "value3"
            }

            self.assertEqual(result, expected_result)
            self.base_generator.llm_tool.execute.assert_called_once()

        asyncio.run(run_test())

    def test_shorten_path_key_with_duplicates(self):
        """Test shorten_path_key with duplicate new keys"""
        key_value_pairs = {
            "long_key_one": "value1",
            "long_key_two": "value2",
        }
        
        # Mock the LLM response with duplicate new keys
        self.base_generator.llm_tool.execute.side_effect = [
            ValueError("Duplicate keys were generated."),
            {
                "tool_calls": [
                    {
                        "name": "shorten_keys",
                        "arguments": {
                            "long_key_one": "unique_key_1",
                            "long_key_two": "unique_key_2"
                        }
                    }
                ]
            }
        ]

        async def run_test():
            # The first call to llm_tool.execute will raise a ValueError,
            # which will be caught by the retry strategy. The retry strategy will
            # then call llm_tool.execute again, which will return the valid response.
            # However, the mock doesn't have the retry logic. So we need to simulate it.
            # The `shorten_path_key` will catch the exception and return the original keys.
            # This is not what we want to test. We want to test the retry logic.
            # The llm_tool is responsible for the retry. The mock should simulate that.
            
            # Let's adjust the side_effect to better mimic the retry loop inside the (mocked) llm_tool
            self.base_generator.llm_tool.execute.side_effect = [
                { # First call, invalid response
                    "tool_calls": [
                        {
                            "name": "shorten_keys",
                            "arguments": {
                                "long_key_one": "duplicate_key",
                                "long_key_two": "duplicate_key"
                            }
                        }
                    ]
                },
                { # Second call, valid response
                    "tool_calls": [
                        {
                            "name": "shorten_keys",
                            "arguments": {
                                "long_key_one": "unique_key_1",
                                "long_key_two": "unique_key_2"
                            }
                        }
                    ]
                }
            ]

            # To properly test this, we need to mock the retry logic within the test,
            # as the mock object itself doesn't have it.
            # Let's assume the `llm_tool.execute` handles retries internally and we just
            # need to provide the sequence of return values. The validator is passed in,
            # but the mock doesn't use it. The test is asserting the final state.
            # The problem is that the first invalid response is returned and processed.

            # The issue is that the `duplicate_key_validator` is what raises the error,
            # and the `llm_tool` is supposed to catch it and retry. The mock doesn't do that.
            # The validator is called *inside* the `llm_tool.execute`.
            # So, the mock needs to simulate this behavior.

            # Let's redefine the mock's behavior for this specific test.
            async def mock_execute_with_retry(*args, **kwargs):
                validators = kwargs.get("validators", [])
                
                # First attempt
                first_response = {
                    "tool_calls": [{"name": "shorten_keys", "arguments": {"long_key_one": "duplicate_key", "long_key_two": "duplicate_key"}}]
                }
                for validator in validators:
                    try:
                        validator(first_response)
                    except ValueError:
                        # Validation failed, simulate retry and return the second, valid response
                        second_response = {
                            "tool_calls": [{"name": "shorten_keys", "arguments": {"long_key_one": "unique_key_1", "long_key_two": "unique_key_2"}}]
                        }
                        return second_response
                return first_response

            self.base_generator.llm_tool.execute = AsyncMock(side_effect=mock_execute_with_retry)

            result = await self.base_generator.shorten_path_key(key_value_pairs)

            expected_result = {
                "unique_key_1": "value1",
                "unique_key_2": "value2",
            }

            self.assertEqual(result, expected_result)
            self.assertEqual(self.base_generator.llm_tool.execute.call_count, 1) # The retry is internal to the mocked execute

        asyncio.run(run_test())
    


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
                input_descriptions, candidate_fields, user_ask, "unit-test-tool", tool_schema
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
                input_descriptions, candidate_fields, user_ask, "unit-test-tool", tool_schema
            )
        
        result = asyncio.run(run_test())
        
        # Should return NOT_FOUND for all fields
        self.assertEqual(result["title"], "<NOT_FOUND_IN_CANDIDATES>")

    def test_generate_input_json_paths_includes_tool_description_in_prompt(self):
        """Ensure Batch flow includes tool_description in the LLM prompt"""
        from tools.json_path_generator import BatchJsonPathGenerator

        tool_description = "unit-test-batch-tool-description"
        llm_tool_mock = MagicMock()
        llm_tool_mock.execute = AsyncMock(return_value={
            "content": "Extraction completed",
            "tool_calls": [
                {
                    "name": "extract_request_parameters",
                    "arguments": {"title": "AI Blog", "topic": "Artificial Intelligence"}
                }
            ]
        })

        generator = BatchJsonPathGenerator(llm_tool=llm_tool_mock)
        generator._analyze_context_candidates = AsyncMock(return_value={})

        async def run_test():
            await generator.generate_input_json_paths(
                {"title": "Blog title", "topic": "Main topic"},
                {"current_task": "Generate blog about AI"},
                tool_description=tool_description,
                user_original_ask="Create AI blog"
            )

        asyncio.run(run_test())

        prompt = llm_tool_mock.execute.call_args[0][0]["prompt"]
        self.assertIn(tool_description, prompt)


class TestOnebyOneJsonPathGeneratorPrompt(unittest.TestCase):
    """Focused regression tests for OnebyOneJsonPathGenerator prompts"""

    def test_generate_input_json_paths_includes_tool_description_in_prompt(self):
        """Ensure One-by-one flow includes tool_description in the LLM prompt"""
        from tools.json_path_generator import OnebyOneJsonPathGenerator

        tool_description = "unit-test-one-by-one-tool-description"

        async def mock_execute(payload, *args, **kwargs):
            # Simulate LLMTool.execute running validators and returning enriched response
            resp = {
                "content": (
                    "<THINK_PROCESS>ok</THINK_PROCESS>\n"
                    "<GENERATED_CODE>\n"
                    "```python\n"
                    "def extract_func(context):\n"
                    "    return 'extracted_value'\n"
                    "```\n"
                    "</GENERATED_CODE>\n"
                )
            }
            for validator in kwargs.get("validators", []):
                validator(resp)
            return resp

        llm_tool_mock = MagicMock()
        llm_tool_mock.execute = AsyncMock(side_effect=mock_execute)

        generator = OnebyOneJsonPathGenerator(llm_tool=llm_tool_mock)
        generator._analyze_context_candidates = AsyncMock(return_value={})

        async def run_test():
            await generator.generate_input_json_paths(
                {"field1": "Test field description"},
                {"current_task": "test task"},
                tool_description=tool_description,
                user_original_ask="Original ask"
            )

        asyncio.run(run_test())

        prompt = llm_tool_mock.execute.call_args[0][0]["prompt"]
        self.assertIn(tool_description, prompt)
   