#!/usr/bin/env python3
"""JSON Path Generator Tool
Uses LLM to generate appropriate JSON paths based on input/output descriptions and context schema

Copyright 2024-2025 Di Chen

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

import json
import asyncio
import re
from typing import Dict, Any, Optional, Tuple
import uuid
from genson import SchemaBuilder
from jsonpath_ng import parse
from contextlib import contextmanager
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from exceptions import TaskInputMissingError
from tools import LLMTool
from utils.json_utils import get_json_path_value


class BaseJsonPathGenerator:
    """Base class providing shared logic for JSON path generation using LLM"""
    
    def __init__(self, llm_tool=None, tracer=None):
        """Initialize JsonPathGenerator with an LLM tool instance and tracer
        
        Args:
            llm_tool: An instance of LLMTool or compatible tool for text generation
            tracer: ExecutionTracer instance for observability (required for production use)
        """
        self.llm_tool = llm_tool
        if self.llm_tool is None:
            self.llm_tool = LLMTool()
        self.tracer = tracer
        if self.tracer is None:
            # For backwards compatibility in tests, create a minimal tracer
            from tracing import ExecutionTracer
            self.tracer = ExecutionTracer(enabled=False)
    

    
    # Intentionally left without generate_input_json_paths; implemented by subclasses
    
    async def generate_output_json_path(
        self, 
        output_description: str, 
        short_name: str,
        context: Dict[str, Any],
        user_original_ask: str = "",
        tool_output: Any = ""
    ) -> str:
        """Generate output JSON path based on output description and context schema
        
        Args:
            output_description: Description of what the output represents
            context: Current context dictionary for schema analysis
            user_original_ask: Original user request for context
            tool_output: Optional tool output content to help determine appropriate path
            
        Returns:
            JSON path string for the output
        """
        if not output_description:
            raise ValueError("Output description cannot be empty")
        
        # Generate context schema representation
        context_schema = self._generate_context_schema(context)
        
        # Create tool schema for generating output path
        tool_schema = self._create_output_path_tool_schema()
        
        # Create prompt for LLM
        prompt = self._create_output_path_prompt(
            output_description, 
            short_name,
            context_schema, 
            user_original_ask,
            tool_output
        )
        
        # Call LLM with tool schema
        response = await self.llm_tool.execute({
            "prompt": prompt,
            "tools": [tool_schema],
            "model": self.llm_tool.small_model  # Use smaller model for efficiency
        })
        
        # Extract tool calls from response
        tool_calls = response.get("tool_calls", [])
        if not tool_calls or len(tool_calls) == 0:
            raise ValueError("LLM did not return any tool calls for output path generation")
        
        # Get the first (and should be only) tool call
        tool_call = tool_calls[0]
        if tool_call.get("name") != "generate_output_path":
            raise ValueError(f"Unexpected tool call: {tool_call.get('name')}")
        
        # Extract arguments
        arguments = tool_call.get("arguments", {})
        path = arguments.get("output_path", "$.output")

        print(f"[JSON_PATH_GEN] Generated output path: {path}")
        return path
    
    def _generate_context_schema(self, context: Dict[str, Any], context_key_meaning_map: Optional[Dict[str, str]] = None) -> str:
        """Generate a readable schema representation of the context
        
        Args:
            context: Current context dictionary
            context_key_meaning_map: Optional mapping from context key -> human meaning (e.g., task short name)
            
        Returns:
            String representation of the context schema
        """
        if not context:
            return "Empty context - no data stored yet"
        
        builder = SchemaBuilder()

        # Exclude _temp_input prefix from context keys
        context_to_builder = {
            key: value for key, value in context.items() if not key.startswith("_temp_input_")
        }

        builder.add_object(context_to_builder)
        properties_str = builder.to_schema()["properties"]

        # Annotate each top-level property with its meaning if provided
        if context_key_meaning_map:
            for key, prop in properties_str.items():
                if isinstance(prop, dict) and key in context_key_meaning_map:
                    # Keep minimal invasive: just add a 'meaning' field
                    prop["meaning"] = context_key_meaning_map[key]

        # Remove all "required" field recursively
        def remove_required_fields(obj):
            if isinstance(obj, dict):
                obj.pop("required", None)
                for value in obj.values():
                    remove_required_fields(value)
            elif isinstance(obj, list):
                for item in obj:
                    remove_required_fields(item)

        remove_required_fields(properties_str)

        return json.dumps(properties_str, ensure_ascii=False, indent=2)
    
    async def _analyze_context_candidates(
        self, 
        input_description: str, 
        context: Dict[str, Any], 
        user_original_ask: str,
        context_key_meaning_map: Optional[Dict[str, str]] = None,
        task_short_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Step 1: Analyze context to find candidate fields for input description
        
        Args:
            input_description: Description of the required input
            context: Current context dictionary
            user_original_ask: Original user request
            context_key_meaning_map: Optional mapping from context key -> human meaning (e.g., task short name)
            task_short_name: Optional short name of the task requesting these inputs
            
        Returns:
            Dictionary of candidate field_name -> field_value pairs
        """
        # If the context length is not too large, just return all fields.
        if len(str(context)) < 1000 and len(context) < 10:
            return {f"$.['{key}']": value for key, value in context.items()}

        context_schema = self._generate_context_schema(context, context_key_meaning_map)
        # Fill short name placeholder; keep backwards compatible if not provided
        short_name_section = task_short_name or "(not provided)"
        prompt = f"""## Task: Find Context Candidates
Analyze the current context to find fields that might contain information for the required input.

## User Original Request
{user_original_ask}

## Request Short Name
{short_name_section}

## Required Input Description
{input_description}

## Current Context Schema
{context_schema}

## Instructions
1. Analyze the context fields to identify which ones might contain relevant information for the input description
2. Return a JSON array with candidate field names
3. Include fields that might be transformed, extracted, or used as-is
4. If no candidates exist, return an empty object
5. Represent the field using json_path syntax, starting with "$." (e.g., "$.['field_name']", "$.['field with spaces']")
6. If there are multiple fields containing the same information, only select one with the shortest field name
7. When the request short name is provided, prefer candidate fields whose meaning or content semantically aligns with it (especially words or entities appearing in the short name). Ignore unrelated fields.

## Return Format (JSON only, no other text)
[
    "candidate_field_1",
    "candidate_field_2"
]"""

        response = await self.llm_tool.execute({
            "prompt": prompt,
        })

        # Extract content from new response format
        response_content = response["content"]

        if "```json" in response_content:
            # Extract JSON array from response
            json_match = re.search(r'```json\n(.*?)\n```', response_content, re.DOTALL)
            if json_match:
                response_content = json_match.group(1).strip()
            else:
                raise ValueError("Response does not contain valid JSON array")
        
        # Parse the JSON response
        candidates = json.loads(response_content)
        # Convert to dictionary with current values, use json_ng json path get
        candidate_content_set = set()
        candidates_objects = {}
        for candidate in candidates:
            try:
                jsonpath_expr = parse(candidate)
                matches = jsonpath_expr.find(context)
                if matches:
                    if str(matches[0].value) in candidate_content_set:
                        # Skip duplicate content
                        continue
                    candidates_objects[candidate] = matches[0].value
                    candidate_content_set.add(str(matches[0].value))
                else:
                    candidates_objects[candidate] = None
            except Exception as e:
                print(f"[JSON_PATH_GEN] Error parsing path {candidate}: {e}")
                candidates_objects[candidate] = None
        print(f"[JSON_PATH_GEN] Found candidates for '{input_description}': {candidates_objects}")
        return candidates_objects            


    def _execute_extraction_code(self, code: str, context: Dict[str, Any]) -> Any:
        """Step 3: Execute the generated extraction code
        
        Args:
            code: Python code string to execute
            context: Current context dictionary
            
        Returns:
            Extracted content
        """
        try:
            # TODO: use sandbox environment for safety
            # Execute the code
            namespace = {}
            namespace["get_json_path_value"] = get_json_path_value
            exec(code, namespace)
            functions = {name: obj for name, obj in namespace.items() if callable(obj) and not name.startswith('__') and name != 'get_json_path_value'}
            if len(functions) != 1:
                raise ValueError("Generated code did not produce a single extraction function")
            extraction_func = functions.popitem()[1]
            result = extraction_func(context)
            
            print(f"[JSON_PATH_GEN] Extracted content: {result}")
            return result
            
        except Exception as e:
            print(f"[JSON_PATH_GEN] Error executing extraction code: {e}")
            print(f"[JSON_PATH_GEN] Code was: {code}")
            # Fallback: return a default value
            raise e

    def cleanup_temp_inputs(self, context: Dict[str, Any]) -> None:
        """Clean up temporary input keys from context
        
        Args:
            context: Context dictionary to clean up
        """
        temp_keys = [key for key in context.keys() if key.startswith('_temp_input_')]
        for key in temp_keys:
            del context[key]
        print(f"[JSON_PATH_GEN] Cleaned up {len(temp_keys)} temporary input keys")
    
    def _create_output_path_tool_schema(self) -> Dict[str, Any]:
        """Create tool schema for generating output JSON path
        
        Returns:
            Tool schema dictionary for use with LLMTool
        """
        tool_schema = {
            "type": "function",
            "function": {
                "name": "generate_output_path",
                "description": "Generate appropriate JSON path for storing tool output in context",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "output_path": {
                            "type": "string",
                            "description": "JSON path using JSONPath syntax (e.g., $.generated_outline_for_xxx_topic_blog, $.['action_plan_to_create_blog_for_xxx']). Should be semantically meaningful and discriminate within the context."
                        }
                    },
                    "required": ["output_path"]
                }
            }
        }
        
        return tool_schema
    
    def _create_output_path_prompt(
        self, 
        output_description: str, 
        short_name: str,
        context_schema: str, 
        user_original_ask: str,
        tool_output: Any = ""
    ) -> str:
        """Create prompt for generating output JSON path"""
        
        if type(tool_output) == dict:
            # Use key as xml tag, wrap the value
            tool_output_str = "\n".join([f"<{key}>\n{value}\n</{key}>" for key, value in tool_output.items()])
        else:
            tool_output_str = str(tool_output)
        
        return f"""## Task Description
Given the following workspace context schema and output description, you MUST use the generate_output_path tool to return the appropriate output JSON path where the result should be stored. If there is obvious error in the output, you should name it with error suffix (e.g., failed_with_xxx_error, etc). Usually you can just use the short name of the User original request's english version, and append suffix to name it. Eg. If short name is "Write a blog about xxx", you can name it as "blog_about_xxx".

## User Original Request
{user_original_ask}

## User Original Request's Short Name
{short_name}

## Current Workspace Context Schema
{context_schema}

## Output Description
{output_description}

## Tool Output
{tool_output_str}

## Instructions
1. Analyze the output description, user original request and tool output to determine the best field name in english snakecase style. Usually you can just use the short name of the User original request's english version, and append suffix to name it. Eg. If short name is "Write a blog about xxx", you can name it as "blog_about_xxx".
2. Consider the existing context schema to avoid conflicts.
3. Return a JSON path using JSONPath syntax (e.g., "$.generated_outline_for_xxx_topic_blog", "$.['action_plan_to_create_blog_for_xxx']"). You should only use root path. Avoid using nested path like "$.some_output_path.some_json_field_in_that_output".
4. The path should be semantically meaningful and discriminate within the context. If a similar path already exists, add more word to discriminate it. 
5. If task short name contains step number like step 3.4.2, please keep it and use camel case for the number, e.g., xx_step_3_4_2_xxx_xxx

## Example 1

If the output description is "The outcome of the current task and the remaining tasks", and the user original request is "Raise 5 questions about machine learning ".

The output can be stored at the path "$.action_plan_for_raising_five_questions_about_machine_learning"

or if the content already generated in the output, the output path might be "$.five_questions_about_machine_learning"

## IMPORTANT: You MUST use the generate_output_path tool function call to provide your response. Do not put the path in your text response. The output path should start with "$." which means the root node."""


class OnebyOneJsonPathGenerator(BaseJsonPathGenerator):
    """Generate JSON paths with a one-by-one, multi-step extraction process"""

    async def _generate_extraction_code(
        self, 
        input_description: str, 
        candidate_fields: Dict[str, Any], 
        context: Dict[str, Any], 
        user_original_ask: str
    ) -> str:
        """Step 2: Generate Python code for content extraction
        
        Args:
            input_description: Description of the required input
            candidate_fields: Candidate fields found in step 1
            context: Current context dictionary
            user_original_ask: Original user request
            
        Returns:
            Python code string for extracting/generating the required content
        """
        candidates_text = "\n".join([
            f"\n<{field}>\n{value}\n</{field}>\n" 
            for field, value in candidate_fields.items() if str(value).strip() != ""
        ])

        candidate_schema = '\n'.join([
            f"    {field}: {type(value).__name__}" 
            for field, value in candidate_fields.items() if str(value).strip() != ""
        ])
        
        prompt = f"""## Task: Generate Parameter Extraction Code
Generate Python code to extract and reformat parameter for the request parameter from candidate fields. User has raise a request and we need to extract and reformat the parameter from the candidate fields in the context. Avoid using f-string when need to fill in variables, use string replacement or concatenation instead.

## User Original Request
{user_original_ask}

## Required Request Parameter Description
{input_description}

## Candidate Fields from Context
Context object is a dictionary, here we represent them using json_path syntax.

The schema:

{candidate_schema}
---
The value:

{candidates_text}
---

## Instructions
1. Generate a Python function that takes 'context' as input variable and returns the code for extracting the request parameter
2. The code can be:
   - Hard-coded information, when the parameter needs some rephrasing: `return "Some fixed string"` or it's so simple (<50 words) that it can be hard-coded.
   - Simple extraction, when the parameter is directly available: `return context['key']`
   - Complex extraction with transformations, regex, string operations, etc, when the parameter needs some transformation.
3. Think if there is info available in context before generating the code. If info is not enough or still have ambiguitiy, use `return "<NOT_FOUND_IN_CANDIDATES>"`. The generated code should just be a getter / parser.
4. The parameter should only be "extracted" or "rephrased", not inferred. This means different people should get the same parameter value if they have the same context, if there is uncertainty, do not rephrase it.
5. If you rephrase the information, make sure you use the same language as the input_description.
6. Just generate the minimum required code, Eg. If there is no requirement to be structured, use plain text. Make sure the code has minimum possibility to fail.
7. The returned parameter should satisfy the requirement from the ## Required Request Parameter Description
8. Use `get_json_path_value(context, 'json_path')` to extract value from context using json_path syntax, instead of directly accessing context dictionary. This will avoid key errors and make the code more robust.

## Examples
```python
# The information is directly available in context, just need to do simple extraction
def extract_func(context):
    return context['some_key'][0]['nested_key']
```

```python
# The information is available in context, but needs some transformation
def extract_func(context): 
    import re
    # Extract content between <title> tags
    return re.match(r'<title>(.*?)</title>', get_json_path_value(context, '$.html_field_json_path.code')).group(1)
```

```python
def extract_func(context): 
    # The information is available in context, but doesn't have extact format, so we rephrase it.
    # Rephrase xxx from xxx
    return "Rephrased content based on context" 
```

```python
def extract_func(context): 
    # The information is already present in context, and it's simple enough to return directly
    return "cat ./some.log | grep 'error' | wc -l" 
```

```python
def extract_func(context):
    # The information is not available in context, return a placeholder also explain why
    return "<NOT_FOUND_IN_CANDIDATES>Cannot find xxx in xxx / Cannot parse xxx"
```

```python
def extract_func(context):
    # Need to combine multiple field, prefer directly assign value to avoid code bug
    images = []
    text = []
    
    # Based on the Candidate Fields from Context schema, image_url_field_1 exists and contains url
    images.append(get_json_path_value(context, '$.image_url_field_1.url'))

    # Based on the Candidate Fields from Context schema, text_field_1 exists and contains required text
    text.append(get_json_path_value(context, '$.text_field_1'))

    result = dict()
    result["images"] = images
    result["text"] = text
    return result
```

## Return Format
<THINK_PROCESS>
...
</THINK_PROCESS>
<GENERATED_CODE>
```python
def extract_func(context):
    return "The extracted parameter value"
```
</GENERATED_CODE>
"""

        response = await self.llm_tool.execute({
            "prompt": prompt
        })
        
        # Extract content from new response format
        response_content = response["content"]
        
        # Print think process for debugging
        print(f"[JSON_PATH_GEN] Think process for '{input_description}': \n{response_content}")
        # Parse using regex to extract the code block
        code_match = re.search(r'```python\n(.*?)\n```', response_content, re.DOTALL)
        if code_match:
            code = code_match.group(1).strip()
        else:
            raise ValueError("Response does not contain valid Python code block")

        print(f"[JSON_PATH_GEN] Generated extraction code for '{input_description}': {code}")
        return code

    async def generate_input_json_paths(
        self,
        input_descriptions: Dict[str, str],
        context: Dict[str, Any],
        user_original_ask: str = "",
        context_key_meaning_map: Optional[Dict[str, str]] = None,
        task_short_name: Optional[str] = None
    ) -> Dict[str, str]:
        """Generate input JSON paths using multi-step process with content extraction

        Args:
            input_descriptions: Dictionary of field_name -> description
            context: Current context dictionary for analysis and extraction
            user_original_ask: Original user request for context
            context_key_meaning_map: Optional mapping from context key -> human meaning (e.g., task short name)

        Returns:
            Dictionary mapping field_name -> json_path, where content is extracted/generated
            and stored in temporary context keys for later use
        """
        if not input_descriptions:
            return {}

        result_paths = {}

        # Process each input description through multi-step analysis
        for field_name, description in input_descriptions.items():
            # Use input field extraction tracing context manager (no-op if tracer disabled)
            with self.tracer.trace_input_field_extraction_step(field_name, description) as input_ctx:
                # Step 1: Analyze context for candidate fields
                candidate_fields = await self._analyze_context_candidates(
                    description, context, user_original_ask, context_key_meaning_map, task_short_name=task_short_name
                )

                # Make sure "current_task" is always included
                if "current_task" not in candidate_fields:
                    candidate_fields["current_task"] = context.get("current_task", "")

                # Step 2: Generate extraction code
                extraction_code = await self._generate_extraction_code(
                    description, candidate_fields, context, user_original_ask
                )

                # Step 3: Execute code and store in temporary context
                temp_key = f"_temp_input_{str(uuid.uuid4())}"
                extracted_content = self._execute_extraction_code(extraction_code, context)
                if "<NOT_FOUND_IN_CANDIDATES>" in extracted_content:
                    # Set error data in context (no-op if tracing disabled)
                    input_ctx.set_result(
                        candidate_fields=candidate_fields,
                        generated_code=extraction_code
                    )
                    # Raise exception without recovery task - that's the engine's job
                    raise TaskInputMissingError(field_name, description)
                else:
                    context[temp_key] = extracted_content
                    # Create JSON path for the temporary key
                    result_paths[field_name] = f"$.['{temp_key}']"

                    print(f"[JSON_PATH_GEN] Generated input for '{field_name}': {extracted_content}")

                    print("Current context after processing:")
                    print(json.dumps(context, ensure_ascii=False, indent=2))

                    # Set successful data in context (no-op if tracing disabled)
                    input_ctx.set_result(
                        candidate_fields=candidate_fields,
                        generated_code=extraction_code,
                        extracted_value=extracted_content,
                        generated_path=f"$.['{temp_key}']"
                    )

        print(f"[JSON_PATH_GEN] Generated input paths: {result_paths}")
        return result_paths


class BatchJsonPathGenerator(BaseJsonPathGenerator):
    """Simplified JSON Path Generator that extracts all input fields at once using LLM tool schema"""
    
    async def generate_input_json_paths(
        self, 
        input_descriptions: Dict[str, str], 
        context: Dict[str, Any],
        user_original_ask: str = "",
        context_key_meaning_map: Optional[Dict[str, str]] = None,
        task_short_name: Optional[str] = None
    ) -> Dict[str, str]:
        """Generate input JSON paths using simplified single-step extraction with LLM tool schema
        
        Args:
            input_descriptions: Dictionary of field_name -> description
            context: Current context dictionary for analysis and extraction
            user_original_ask: Original user request for context
            context_key_meaning_map: Optional mapping from context key -> human meaning (e.g., task short name)
            
        Returns:
            Dictionary mapping field_name -> json_path, where content is extracted
            and stored in temporary context keys for later use
        """
        if not input_descriptions:
            return {}
            
        result_paths = {}
        
        # Use batch extraction tracing context manager
        with self.tracer.batch_extract_input_field(input_descriptions) as batch_ctx:
            # Step 1: Analyze context for ALL candidate fields at once
            # Get all field descriptions for context analysis
            all_descriptions = "\n".join([f"- {field_name}: {description}" 
                                        for field_name, description in input_descriptions.items()])
            
            candidate_fields = await self._analyze_context_candidates(
                all_descriptions, context, user_original_ask, context_key_meaning_map, task_short_name=task_short_name
            )
            
            # Make sure "current_task" is always included
            if "current_task" not in candidate_fields:
                candidate_fields["current_task"] = context.get("current_task", "")
            
            # Step 2: Create tool schema for extracting all fields
            tool_schema = self._create_extraction_tool_schema(input_descriptions)
            
            # Step 3: Use LLM tool to extract all fields at once
            extracted_values = await self._extract_all_fields_with_llm(
                input_descriptions, candidate_fields, user_original_ask, tool_schema
            )
            
            # Step 4: Process results and create JSON paths
            generated_paths = {}
            for field_name, extracted_content in extracted_values.items():
                if extracted_content == "<NOT_FOUND_IN_CANDIDATES>":
                    # Record data for debugging and raise exception
                    batch_ctx.set_result(
                        candidate_fields=candidate_fields,
                        tool_schema=tool_schema,
                        extracted_values=extracted_values
                    )
                    raise TaskInputMissingError(field_name, input_descriptions[field_name])
                else:
                    # Create temporary key and store content
                    temp_key = f"_temp_input_{str(uuid.uuid4())}"
                    context[temp_key] = extracted_content
                    json_path = f"$.['{temp_key}']"
                    result_paths[field_name] = json_path
                    generated_paths[field_name] = json_path

                    print(f"[SIMPLE_JSON_PATH_GEN] Generated input for '{field_name}': {extracted_content}")
            
            # Set successful data in tracer context (no-op if tracer disabled)
            batch_ctx.set_result(
                candidate_fields=candidate_fields,
                tool_schema=tool_schema,
                extracted_values=extracted_values,
                generated_paths=generated_paths
            )
        
        print(f"[SIMPLE_JSON_PATH_GEN] Generated input paths: {result_paths}")
        return result_paths
    
    def _create_extraction_tool_schema(self, input_descriptions: Dict[str, str]) -> Dict[str, Any]:
        """Create tool schema for extracting all input fields
        
        Args:
            input_descriptions: Dictionary of field_name -> description
            
        Returns:
            Tool schema dictionary for use with LLMTool
        """
        # Create properties for each field
        properties = {}
        required_fields = []
        
        for field_name, description in input_descriptions.items():
            properties[field_name] = {
                "type": "string",
                "description": description
            }
            required_fields.append(field_name)
        
        tool_schema = {
            "type": "function",
            "function": {
                "name": "extract_request_parameters",
                "description": "Extract and reformat request parameters from candidate fields in context",
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required_fields
                }
            }
        }
        
        return tool_schema
    
    async def _extract_all_fields_with_llm(
        self,
        input_descriptions: Dict[str, str],
        candidate_fields: Dict[str, Any], 
        user_original_ask: str,
        tool_schema: Dict[str, Any]
    ) -> Dict[str, str]:
        """Extract all input fields at once using LLM with tool schema
        
        Args:
            input_descriptions: Dictionary of field_name -> description
            candidate_fields: Candidate fields from context analysis
            user_original_ask: Original user request
            tool_schema: Tool schema for extraction
            
        Returns:
            Dictionary mapping field_name -> extracted_content
        """
        # Format candidate fields for display
        candidates_text = "\n".join([
            f"<{field_path}>\n{value}\n</{field_path}>\n\n" 
            for field_path, value in candidate_fields.items()
        ])
        
        # Format input descriptions for display  
        input_description_list = "\n".join([
            f"- {field_name}: {description}"
            for field_name, description in input_descriptions.items()
        ])
        
        # Create prompt using the template from requirements
        prompt = f"""## Task: Extract request parameter
User has raise a request and we need to extract and reformat the parameter from the candidate fields in the context. These parameter will be used for a tool: {getattr(self, 'tool_description', 'General purpose tool')}

## User Original Request
{user_original_ask}

## Required Request Parameter Description
{input_description_list}

## Candidate Fields from Context
Context object is a dictionary, here we represent them using json_path syntax:
{candidates_text}

## Instructions
1. Extract the request parameter from candidate fields from text. You can rephrase the wording to make it more suitable for this task.
2. The parameter should only be "extracted" or "rephrased", not inferred. This means different people should get the same parameter value if they have the same context, if there is uncertainty, do not rephrase it.
3. If there is no perfect match, put string "<NOT_FOUND_IN_CANDIDATES>" in corresponding field.
4. If you rephrase the information, make sure you use the same language as the input_description.

## Return the parameter using tool schema"""
        
        # Call LLM with tool schema
        response = await self.llm_tool.execute({
            "prompt": prompt,
            "tools": [tool_schema]
        })
        
        # Extract tool calls from response
        tool_calls = response.get("tool_calls", [])
        if not tool_calls:
            # Fallback: return NOT_FOUND for all fields
            return {field_name: "<NOT_FOUND_IN_CANDIDATES>" 
                   for field_name in input_descriptions.keys()}
        
        # Get the first (and should be only) tool call
        tool_call = tool_calls[0]
        if tool_call.get("name") != "extract_request_parameters":
            raise ValueError(f"Unexpected tool call: {tool_call.get('name')}")
        
        # Extract arguments
        arguments = tool_call.get("arguments", {})
        
        print(f"[SIMPLE_JSON_PATH_GEN] LLM extracted fields: {arguments}")
        
        # Ensure all required fields are present
        result = {}
        for field_name in input_descriptions.keys():
            result[field_name] = arguments.get(field_name, "<NOT_FOUND_IN_CANDIDATES>")
        
        return result



# Example usage and testing
async def test_json_path_generator():
    """Test the JSON path generator with multi-step content extraction"""
    generator = OnebyOneJsonPathGenerator()
    
    # Test context
    test_context = {
        "current_task": "Please generate a blog outline for a blog titled 'The Future of Artificial Intelligence'",
        "user_learning_purpose": "Understand AI technology development"
    }
    
    print("Initial context:")
    print(json.dumps(test_context, ensure_ascii=False, indent=2))
    
    # Test input path generation with new multi-step process
    input_descriptions = {
        "title": "The title of the blog for which we want to generate an outline",
        "user_ask": "Task requirements or user's original input",
        "topic": "The main topic of the blog"
    }
    
    print("\nTesting multi-step input path generation...")
    input_paths = await generator.generate_input_json_paths(
        input_descriptions, 
        test_context, 
        test_context["current_task"]
    )
    print(f"Generated input paths: {input_paths}")
    
    print("\nContext after input processing:")
    print(json.dumps(test_context, ensure_ascii=False, indent=2))
    
    # Test output path generation  
    output_description = "Blog outline generated based on blog title and writing purpose"
    short_name = "Generate blog outline"
    
    print("\nTesting output path generation...")
    output_path = await generator.generate_output_json_path(
        output_description,
        short_name,
        test_context,
        "Please generate a blog outline for artificial intelligence topic"
    )
    print(f"Generated output path: {output_path}")
    
    # Test cleanup
    print("\nTesting cleanup...")
    generator.cleanup_temp_inputs(test_context)
    print("Context after cleanup:")
    print(json.dumps(test_context, ensure_ascii=False, indent=2))


async def test_simple_json_path_generator():
    """Test the simplified JSON path generator"""
    generator = BatchJsonPathGenerator()
    
    # Test context
    test_context = {
        "current_task": "Please generate a blog outline for a blog titled 'The Future of Artificial Intelligence'",
        "user_learning_purpose": "Understand AI technology development"
    }
    
    print("Initial context:")
    print(json.dumps(test_context, ensure_ascii=False, indent=2))
    
    # Test input path generation with simplified process
    input_descriptions = {
        "title": "The title of the blog for which we want to generate an outline",
        "user_ask": "Task requirements or user's original input",
        "topic": "The main topic of the blog"
    }
    
    print("\nTesting simplified input path generation...")
    input_paths = await generator.generate_input_json_paths(
        input_descriptions, 
        test_context, 
        test_context["current_task"]
    )
    print(f"Generated input paths: {input_paths}")
    
    print("\nContext after input processing:")
    print(json.dumps(test_context, ensure_ascii=False, indent=2))
    
    # Test cleanup
    print("\nTesting cleanup...")
    generator.cleanup_temp_inputs(test_context)
    print("Context after cleanup:")
    print(json.dumps(test_context, ensure_ascii=False, indent=2))


class SmartJsonPathGenerator(BaseJsonPathGenerator):
    """Smart JSON Path Generator that routes between OneByOneJsonPathGenerator and BatchJsonPathGenerator
    based on the input criteria."""
    
    def __init__(self, llm_tool=None, tracer=None):
        """Initialize SmartJsonPathGenerator with generator instances
        
        Args:
            llm_tool: An instance of LLMTool or compatible tool for text generation
            tracer: ExecutionTracer instance for observability (required for production use)
        """
        super().__init__(llm_tool, tracer)
        
        # Initialize both generator instances to avoid code duplication
        self.one_by_one_generator = OnebyOneJsonPathGenerator(llm_tool, tracer)
        self.batch_generator = BatchJsonPathGenerator(llm_tool, tracer)
    
    async def generate_input_json_paths(
        self,
        input_descriptions: Dict[str, str],
        context: Dict[str, Any],
        user_original_ask: str = "",
        context_key_meaning_map: Optional[Dict[str, str]] = None,
        task_short_name: Optional[str] = None
    ) -> Dict[str, str]:
        """Generate input JSON paths by routing to appropriate generator
        
        Args:
            input_descriptions: Dictionary of field_name -> description
            context: Current context dictionary for analysis and extraction
            user_original_ask: Original user request for context
            context_key_meaning_map: Optional mapping from context key -> human meaning (e.g., task short name)
            
        Returns:
            Dictionary mapping field_name -> json_path
        """
        if not input_descriptions:
            return {}
        
        # Route based on input criteria:
        # 1. If len(input_descriptions) == 1, use OneByOneJsonPathGenerator
        # 2. Others use BatchJsonPathGenerator
        if len(input_descriptions) == 1:
            print(f"[SMART_JSON_PATH_GEN] Using OneByOneJsonPathGenerator for single input")
            return await self.one_by_one_generator.generate_input_json_paths(
                input_descriptions, context, user_original_ask, context_key_meaning_map, task_short_name=task_short_name
            )
        else:
            print(f"[SMART_JSON_PATH_GEN] Using BatchJsonPathGenerator for {len(input_descriptions)} inputs")
            return await self.batch_generator.generate_input_json_paths(
                input_descriptions, context, user_original_ask, context_key_meaning_map, task_short_name=task_short_name
            )


if __name__ == "__main__":
    print("=== Testing OnebyOneJsonPathGenerator ===")
    asyncio.run(test_json_path_generator())

    print("\n=== Testing BatchJsonPathGenerator ===")
    asyncio.run(test_simple_json_path_generator())
