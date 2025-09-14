#!/usr/bin/env python3
"""CLI Tool for Doc Flow Agent
Tool for executing command line interface commands

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

import asyncio
from typing import Dict, Any, Optional

from .base_tool import BaseTool
from .llm_tool import LLMTool


class CLITool(BaseTool):
    """Command Line Interface tool for executing shell commands.

    Enhancement: If the 'command' parameter is NOT provided, the tool will use the LLM
    (via `LLMTool`) to synthesize a safe command from a 'task_description' (and optional
    'related_context_content'). This mirrors how `PythonExecutorTool` generates code
    when 'python_code' is absent.
    """

    def __init__(self, llm_tool: Optional[LLMTool] = None):
        super().__init__("CLI")
        self.llm_tool = llm_tool  # May be None if only explicit commands are desired

    async def execute(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute CLI tool with given parameters.

    Accepted parameter patterns:
    1. {'command': '<explicit shell command>'}
    2. {'task_description': 'describe what to do'} (command will be generated if missing)

        Returns:
            Dict with keys: stdout, stderr, returncode, generated_command (optional)

        Raises:
            ValueError: If required parameters missing for both explicit or generated mode
            RuntimeError: If command execution fails / unsafe command detected
        """
        explicit_command = parameters.get('command')
        generated_command = None

        if not explicit_command:
            # Need to generate a command
            if self.llm_tool is None:
                raise ValueError("LLM tool not provided; cannot generate command")

            task_description = parameters.get('task_description')
            if not task_description:
                raise ValueError("Either 'command' or 'task_description' must be supplied")

            tool_schema = self._create_command_generation_tool_schema()
            # related_context_content is deprecated for CLI; ignore if provided
            prompt = self._build_generation_prompt(task_description)

            llm_params = {
                "prompt": prompt,
                "temperature": 0.0,
                "tools": [tool_schema]
            }
            response = await self.llm_tool.execute(llm_params)
            generated_command = self._extract_command_from_response(response)
            explicit_command = generated_command

        print(f"[CLI CALL] Command: {explicit_command}")

        process = await asyncio.create_subprocess_shell(
            explicit_command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            raise RuntimeError(f"CLI command failed (code {process.returncode}): {stderr.decode()}")

        return {
            "stdout": stdout.decode(),
            "stderr": stderr.decode(),
            "returncode": process.returncode,
            "executed_command": explicit_command,
        }

    def _create_command_generation_tool_schema(self) -> Dict[str, Any]:
        """Tool schema for LLM command generation."""
        return {
            "type": "function",
            "function": {
                "name": "generate_command",
                "description": "Generate a shell command to accomplish the described task.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "command": {
                            "type": "string",
                            "description": "A shell command. Prefer POSIX utilities (echo, ls, cat)."
                        }
                    },
                    "required": ["command"]
                }
            }
        }

    def _build_generation_prompt(self, task_description: str) -> str:
        return f"""You are a command generation assistant.
Generate shell command to perform the task.
Rules:
1. The command should be able to run in bash with no additional input from stdin.
2. Output MUST be returned via generate_command tool call.

<Task Description>
{task_description}
</Task Description>
"""

    def _extract_command_from_response(self, response) -> str:
        if isinstance(response, str):
            return response.strip()
        tool_calls = response.get("tool_calls", []) if isinstance(response, dict) else []
        if not tool_calls:
            # fallback: attempt to parse content as plain text
            content = response.get("content", "") if isinstance(response, dict) else ""
            return content.strip()
        tool_call = tool_calls[0]
        if tool_call.get("name") != "generate_command":
            raise ValueError(f"Unexpected tool call: {tool_call.get('name')}")
        arguments = tool_call.get("arguments", {})
        command = arguments.get("command", "").strip()
        if not command:
            raise ValueError("No command generated by LLM")
        return command