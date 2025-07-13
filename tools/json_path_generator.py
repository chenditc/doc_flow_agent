#!/usr/bin/env python3
"""
JSON Path Generator Tool
Uses LLM to generate appropriate JSON paths based on input/output descriptions and context schema
"""

import json
import asyncio
import re
from typing import Dict, Any, Optional, Tuple
import uuid
from genson import SchemaBuilder
from jsonpath_ng import parse
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from exceptions import TaskInputMissingError
from tools import LLMTool


class JsonPathGenerator:
    """Generate JSON paths for SOP documents using LLM"""
    
    def __init__(self, llm_tool = None):
        """Initialize JsonPathGenerator with an LLM tool instance
        
        Args:
            llm_tool: An instance of LLMTool or compatible tool for text generation
        """
        self.llm_tool = llm_tool
        if self.llm_tool is None:
            self.llm_tool = LLMTool()
        
    
    async def generate_input_json_paths(
        self, 
        input_descriptions: Dict[str, str], 
        context: Dict[str, Any],
        user_original_ask: str = ""
    ) -> Dict[str, str]:
        """Generate input JSON paths using multi-step process with content extraction
        
        Args:
            input_descriptions: Dictionary of field_name -> description
            context: Current context dictionary for analysis and extraction
            user_original_ask: Original user request for context
            
        Returns:
            Dictionary mapping field_name -> json_path, where content is extracted/generated 
            and stored in temporary context keys for later use
        """
        if not input_descriptions:
            return {}
        
        result_paths = {}
        
        # Process each input description through multi-step analysis
        for field_name, description in input_descriptions.items():
            try:
                # Step 1: Analyze context for candidate fields
                candidate_fields = await self._analyze_context_candidates(
                    description, context, user_original_ask
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
                if extracted_content == "<NOT_FOUND_IN_CANDIDATES>":
                    # Raise exception without recovery task - that's the engine's job
                    raise TaskInputMissingError(field_name, description)
                else:
                    context[temp_key] = extracted_content
                    # Create JSON path for the temporary key
                    result_paths[field_name] = f"$.['{temp_key}']"

                    print(f"[JSON_PATH_GEN] Generated input for '{field_name}': {extracted_content}")

                    print("Current context after processing:")
                    print(json.dumps(context, ensure_ascii=False, indent=2))
            except Exception as e:
                print(f"[JSON_PATH_GEN] Error processing '{field_name}': {e}")
                raise e
        
        print(f"[JSON_PATH_GEN] Generated input paths: {result_paths}")
        return result_paths
    
    async def generate_output_json_path(
        self, 
        output_description: str, 
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
        
        # Create prompt for LLM
        prompt = self._create_output_path_prompt(
            output_description, 
            context_schema, 
            user_original_ask,
            tool_output
        )
        
        # Call LLM
        try:
            response = await self.llm_tool.execute({
                "prompt": prompt,
                "step": "json_path_output_generation"
            })
            
            # Extract the generated path
            try:
                path_data = json.loads(response)
                path = path_data.get("output_path", "$.output")
            except json.JSONDecodeError:
                # If content is not JSON, try to extract path from text
                content = response.strip()
                if content.startswith("$.") or content.startswith("$["):
                    path = content
                else:
                    path = "$.output"

            print(f"[JSON_PATH_GEN] Generated output path: {path}")
            return path
            
        except Exception as e:
            print(f"[JSON_PATH_GEN] Error generating output path: {e}")
            # Fallback: generate simple path based on description
            return "$.output"
    
    def _generate_context_schema(self, context: Dict[str, Any]) -> str:
        """Generate a readable schema representation of the context
        
        Args:
            context: Current context dictionary
            
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
        return json.dumps(properties_str, ensure_ascii=False, indent=2)
    
    async def _analyze_context_candidates(
        self, 
        input_description: str, 
        context: Dict[str, Any], 
        user_original_ask: str
    ) -> Dict[str, Any]:
        """Step 1: Analyze context to find candidate fields for input description
        
        Args:
            input_description: Description of the required input
            context: Current context dictionary
            user_original_ask: Original user request
            
        Returns:
            Dictionary of candidate field_name -> field_value pairs
        """
        # If the context length is not too large, just return all fields.
        if len(str(context)) < 1000 and len(context) < 10:
            return {f"$.['{key}']": value for key, value in context.items()}

        context_schema = self._generate_context_schema(context)
        
        prompt = f"""## Task: Find Context Candidates
Analyze the current context to find fields that might contain information for the required input.

## User Original Request
{user_original_ask}

## Required Input Description
{input_description}

## Current Context Schema
{context_schema}

## Instructions
1. Analyze the context fields to identify which ones might contain relevant information for the input description
2. Return a JSON array with candidate field names
3. Include fields that might be transformed, extracted, or used as-is
4. If no candidates exist, return an empty object
5. Represent the field using json_path syntax (e.g., "$.['field_name']", "$['field with spaces']")

## Return Format (JSON only, no other text)
[
    "candidate_field_1",
    "candidate_field_2"
]"""

        response = await self.llm_tool.execute({
            "prompt": prompt,
            "step": "json_path_analyze_context_candidates"
        })

        if "```json" in response:
            # Extract JSON array from response
            json_match = re.search(r'```json\n(.*?)\n```', response, re.DOTALL)
            if json_match:
                response = json_match.group(1).strip()
            else:
                raise ValueError("Response does not contain valid JSON array")
        
        # Parse the JSON response
        candidates = json.loads(response)
        # Convert to dictionary with current values, use json_ng json path get
        candidates_objects = {}
        for candidate in candidates:
            try:
                jsonpath_expr = parse(candidate)
                matches = jsonpath_expr.find(context)
                if matches:
                    candidates_objects[candidate] = matches[0].value
                else:
                    candidates_objects[candidate] = None
            except Exception as e:
                print(f"[JSON_PATH_GEN] Error parsing path {candidate}: {e}")
                candidates_objects[candidate] = None
        print(f"[JSON_PATH_GEN] Found candidates for '{input_description}': {candidates_objects}")
        return candidates_objects            

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
            f"- {field}: {value}" 
            for field, value in candidate_fields.items()
        ])
        
        prompt = f"""## Task: Generate Parameter Extraction Code
Generate Python code to extract and reformat parameter for the request parameter from candidate fields. User has raise a request and we need to extract and reformat the parameter from the candidate fields in the context.

## User Original Request
{user_original_ask}

## Required Request Parameter Description
{input_description}

## Candidate Fields from Context
Context object is a dictionary, here we represent them using json_path syntax:
{candidates_text}

## Instructions
1. Generate a Python function that takes 'context' as input variable and returns the code for extracting the request parameter
2. The code can be:
   - Hard-coded information, when the parameter needs some rephrasing: `return "Some fixed string"` or it's so simple (<50 words) that it can be hard-coded.
   - Simple extraction, when the parameter is directly available: `return context['key']`
   - Complex extraction with transformations, regex, string operations, etc, when the parameter needs some transformation.
3. Think if there is info available in context before generating the code. If info is not enough or still have ambiguitiy, use `return "<NOT_FOUND_IN_CANDIDATES>"`. The generated code should just be a getter / parser.
4. The parameter should only be "extracted" or "rephrased", not inferred. This means different people should get the same parameter value if they have the same context, if there is uncertainty, do not rephrase it.
5. If there is no perfect match, return a piece of code which return "<NOT_FOUND_IN_CANDIDATES>".

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
    return re.match(r'<title>(.*?)</title>', context.get('html', '')).group(1)
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
    # The information is not available in context, return a placeholder
    return "<NOT_FOUND_IN_CANDIDATES>"
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

        try:
            response = await self.llm_tool.execute({
                "prompt": prompt,
                "step": "json_path_generate_extraction_code"
            })
            # Print think process for debugging
            print(f"[JSON_PATH_GEN] Think process for '{input_description}': {response}")
            # Parse using regex to extract the code block
            code_match = re.search(r'```python\n(.*?)\n```', response, re.DOTALL)
            if code_match:
                code = code_match.group(1).strip()
            else:
                raise ValueError("Response does not contain valid Python code block")
            
            print(f"[JSON_PATH_GEN] Generated extraction code for '{input_description}': {code}")
            return code
        except Exception as e:
            print(f"[JSON_PATH_GEN] Error generating extraction code: {e}")
            # Fallback: return lambda that returns description
            return f'lambda context: "{input_description}"'
    
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
            exec(code, namespace)
            functions = {name: obj for name, obj in namespace.items() if callable(obj) and not name.startswith('__')}
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
    
    def _create_output_path_prompt(
        self, 
        output_description: str, 
        context_schema: str, 
        user_original_ask: str,
        tool_output: Any = ""
    ) -> str:
        """Create prompt for generating output JSON path"""
        
        tool_output_str = str(tool_output)
        
        return f"""## Task Description
Given the following workspace context schema and output description, return the appropriate output JSON path where the result should be stored.

## User Original Request
{user_original_ask}

## Current Workspace Context Schema
{context_schema}

## Output Description
{output_description}

## Tool Output
{tool_output_str}

## Instructions
1. Analyze the output description, user original request and tool output to determine the best field name in english snakecase style.
2. Consider the existing context schema to avoid conflicts
3. Return a JSON path using JSONPath syntax (e.g., "$.generated_outline_for_xxx_topic_blog", "$.['action_plan_to_create_blog_for_xxx']")
4. The path should be semantically meaningful and discriminate within the context. If a similar path already exists, add more word to discriminate it.

## Example 1

If the output description is "The outcome of the current task and the remaining tasks", and the user original request is "Raise 5 questions about machine learning ".

The output can be stored at the path:
```json
{{
   "output_path": "$.action_plan_for_raising_five_questions_about_machine_learning"
}}
```

or if the content already generated in the output, the output path might be:
```json
{{
   "output_path": "$.five_questions_about_machine_learning"
}}
```

## Return Format (JSON only, no other text)
{{
   "output_path": "$.appropriate_path"
}}"""


# Example usage and testing
async def test_json_path_generator():
    """Test the JSON path generator with multi-step content extraction"""
    generator = JsonPathGenerator()
    
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
    
    print("\nTesting output path generation...")
    output_path = await generator.generate_output_json_path(
        output_description,
        test_context,
        "Please generate a blog outline for artificial intelligence topic"
    )
    print(f"Generated output path: {output_path}")
    
    # Test cleanup
    print("\nTesting cleanup...")
    generator.cleanup_temp_inputs(test_context)
    print("Context after cleanup:")
    print(json.dumps(test_context, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(test_json_path_generator())
