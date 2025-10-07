#!/usr/bin/env python3
"""Python Executor Tool for Doc Flow Agent

Generates and runs safe Python functions via LLM assistance.

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
import subprocess
import uuid
from typing import Any, Dict, Optional, List
import os
import sys
from importlib import metadata as importlib_metadata

from dotenv import load_dotenv
from tools.base_tool import BaseTool
from tools.llm_tool import LLMTool

# Load environment variables from .env file
load_dotenv()


class PythonExecutorTool(BaseTool):
    def __init__(self, llm_tool: LLMTool, max_generation_attempts: int = 3):
        super().__init__("PYTHON_EXECUTOR")
        if max_generation_attempts < 1:
            raise ValueError("max_generation_attempts must be at least 1")

        self.llm_tool = llm_tool
        self.max_generation_attempts = max_generation_attempts

    async def execute(self, parameters: Dict[str, Any], sop_doc_body: str = "") -> Dict[str, Any]:
        task_description = parameters.get("task_description")
        related_context_content = parameters.get("related_context_content", {})

        python_code = parameters.get("python_code")
        if not python_code:
            # Create tool schema for Python code generation
            tool_schema = self._create_python_code_tool_schema()

            sop_guidance = ""
            if sop_doc_body.strip():
                sop_guidance = f"<Document Guidance>\n{sop_doc_body.strip()}\n</Document Guidance>\n"

            # Collect available top-level python libraries to guide generation (limits hallucination)
            available_libs = self._get_available_python_libraries()

            prompt = f"""
You are a Python code generation assistant.
Your task is to write a single Python function named `process_step` that takes one argument: `context: {type(related_context_content).__name__}`.
This function will be executed to perform following specific task. Import necessary library if you used any.
The context object will contain all the necessary data. The json serialized context object has been attached here for you to understand the input data structure.
The function should return a JSON-serializable value.

<available library>
{available_libs}
</available library>

<Task Description>
{task_description}
</Task Description>
{sop_guidance}
<context object type>{type(related_context_content).__name__}</context object type>
<Json serialized context object>
{json.dumps(related_context_content, indent=2, ensure_ascii=False)}
</Json serialized context object>
"""

            llm_params = {
                "prompt": prompt,
                "temperature": 0.0,
                "tools": [tool_schema]
            }

            for attempt in range(1, self.max_generation_attempts + 1):
                response = await self.llm_tool.execute(llm_params)

                # Extract generated code from tool call response
                candidate_code = self._extract_python_code_from_response(response)

                # Ensure the generated code is a string
                if not isinstance(candidate_code, str):
                    candidate_code = str(candidate_code)

                try:
                    compile(candidate_code, "<generated_code>", "exec")
                    python_code = candidate_code
                    break
                except SyntaxError as error:
                    if attempt >= self.max_generation_attempts:
                        raise SyntaxError(
                            f"LLM failed to produce syntactically valid Python code after {self.max_generation_attempts} attempts"
                        ) from error
                    # Retry with a fresh generation
                    continue

            if not python_code:
                # This should not happen, but guard against it
                raise RuntimeError("Failed to obtain Python code from LLM")
        else:
            if not isinstance(python_code, str):
                python_code = str(python_code)

        # Prepare for subprocess
        run_id = uuid.uuid4()
        context_file = f"/tmp/context_{run_id}.json"
        code_file = f"/tmp/code_{run_id}.py"
        output_file = f"/tmp/result_{run_id}.json"

        with open(context_file, "w") as f:
            json.dump(related_context_content, f)

        with open(code_file, "w") as f:
            f.write(python_code)

        try:
            # Run subprocess
            command = [
                sys.executable,
                "tools/executor_runner.py",
                "--code-file",
                code_file,
                "--context-file",
                context_file,
                "--output-file",
                output_file,
            ]
            process = subprocess.run(
                command, capture_output=True, text=True, check=False
            )

            # Process results
            if os.path.exists(output_file):
                with open(output_file, "r") as f:
                    result_data = json.load(f)
            else:
                result_data = {"return_value": None, "exception": "Output file not found."}

            return_value = result_data.get("return_value")
            exception_details = result_data.get("exception")

        finally:
            # Clean up temporary files
            for file_path in [context_file, code_file, output_file]:
                if os.path.exists(file_path):
                    os.remove(file_path)

        return {
            "python_code": python_code,
            "return_value": return_value,
            "stdout": process.stdout,
            "stderr": process.stderr,
            "exception": exception_details,
        }

    def _get_available_python_libraries(self, limit: int = 300) -> str:
        """Return a newline separated list of available installed top-level libraries.

        We only expose a capped, alphabetically sorted set of distinct distribution names to
        the model to reduce prompt size and guide import choices. Internal / meta packages
        (like dist-info) are filtered out. If collection fails we return an empty string.

        Args:
            limit: maximum number of package names to include to keep prompt concise.
        """
        dists = list(importlib_metadata.distributions())
        names: List[str] = []
        for d in dists:
            name = d.metadata.get("Name") or d.metadata.get("Summary") or ""
            if not name:
                continue
            # Normalize
            name = name.strip()
            # Basic filters
            if not name or name.startswith(('_', 'python-')):
                continue
            if name.endswith('.dist-info'):
                continue
            names.append(name)
        # De-duplicate preserving order
        seen = set()
        unique = []
        for n in names:
            k = n.lower()
            if k in seen:
                continue
            seen.add(k)
            unique.append(n)
        unique = sorted(unique, key=lambda x: x.lower())[:limit]
        return "\n".join(unique)

    def _create_python_code_tool_schema(self) -> Dict[str, Any]:
        """Create tool schema for Python code generation
        
        Returns:
            Tool schema dictionary for use with LLMTool
        """
        tool_schema = {
            "type": "function",
            "function": {
                "name": "generate_python_code",
                "description": "Generate Python code for the process_step function",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "python_code": {
                            "type": "string",
                            "description": "Complete Python function definition for process_step(context: dict) that performs the requested task"
                        }
                    },
                    "required": ["python_code"]
                }
            }
        }
        
        return tool_schema

    def _extract_python_code_from_response(self, response) -> str:
        """Extract Python code from LLM response with tool calls
        
        Args:
            response: LLM response containing tool calls
            
        Returns:
            Generated Python code as string
        """
        # Handle both string response (legacy) and tool call response
        if isinstance(response, str):
            return response
            
        # Extract tool calls from response
        tool_calls = response.get("tool_calls", [])
        if not tool_calls:
            # Fallback to direct response if no tool calls
            return str(response)
        
        # Get the first (and should be only) tool call
        tool_call = tool_calls[0]
        if tool_call.get("name") != "generate_python_code":
            raise ValueError(f"Unexpected tool call: {tool_call.get('name')}")
        
        # Extract arguments
        arguments = tool_call.get("arguments", {})
        python_code = arguments.get("python_code", "")
        
        if not python_code:
            raise ValueError("No Python code generated by LLM")
            
        return python_code

    def get_result_validation_hint(self) -> str:
        return "The result is a JSON object with keys: python_code (string), return_value (any), stdout (string), stderr (string), exception (string or null). Check for obvious errors in exception and stderr. If exception is not null, the code execution failed. Ensure return_value is relevant to the task description and satisfies task requirements."