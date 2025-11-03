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
import os
from typing import Dict, Any, Optional, List, Set

from .base_tool import BaseTool
from .llm_tool import LLMTool
import httpx


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

    async def execute(self, parameters: Dict[str, Any], sop_doc_body: str = "") -> Dict[str, Any]:
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
        explicit_command = parameters.get('command', '')
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
            executables = self._get_available_executables()
            prompt = self._build_generation_prompt(task_description, sop_doc_body, executables)

            llm_params = {
                "prompt": prompt,
                "temperature": 0.0,
                "tools": [tool_schema]
            }
            response = await self.llm_tool.execute(llm_params)
            generated_command = self._extract_command_from_response(response)
            explicit_command = generated_command

        # Always execute in sandbox; raise if not configured
        sandbox_base = self._get_sandbox_base_url()
        if not sandbox_base:
            raise ValueError("WORKSPACE_SANDBOX_URL/DEFAULT_WORKSPACE_SANDBOX_URL is not set; sandbox execution is required")

        result = await self._exec_in_sandbox(
            explicit_command,
            exec_dir=parameters.get("exec_dir"),
            id=parameters.get("id"),
            async_mode=parameters.get("async_mode"),
            timeout=parameters.get("timeout"),
        )

        # Preserve backwards-compatible keys; add 'success' boolean for convenience.
        result.setdefault("executed_command", explicit_command)
        result.setdefault("success", (result.get("returncode", 1) == 0))
        return result

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

    def _build_generation_prompt(self, task_description: str, sop_doc_body: str, executables: List[str]) -> str:
        document_guidance = ""
        if sop_doc_body.strip():
            document_guidance = f"<Document Guidance>\n{sop_doc_body.strip()}\n</Document Guidance>\n"
        exec_block = "\n".join(executables)
        return f"""You are a command generation assistant.
Generate shell command to perform the task.
Rules:
1. The command should be able to run in bash with no additional input from stdin.
2. Output MUST be returned via generate_command tool call.

<Example command>
ls -la /home/user/documents | grep '.txt'
</Example command>

<available executables>
{exec_block}
</available executables>

{document_guidance}

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

    def _get_available_executables(self, limit: int = 120) -> List[str]:
        """Return a sorted list of executable command names found on PATH.

        We gather unique file names that are executable. Hidden files and names with spaces
        are skipped to reduce noise. The list is truncated to `limit` entries for prompt size.
        """
        path_env = os.environ.get("PATH", "")
        seen: Set[str] = set()
        execs: List[str] = []
        for directory in path_env.split(":"):
            if not directory or not os.path.isdir(directory):
                continue
            try:
                for entry in os.listdir(directory):
                    if entry.startswith('.'):
                        continue
                    if '.' in entry and not entry.endswith('.exe'):
                        continue
                    if ' ' in entry:
                        continue
                    if entry in seen:
                        continue
                    full_path = os.path.join(directory, entry)
                    if not os.path.isfile(full_path):
                        continue
                    if os.access(full_path, os.X_OK):
                        seen.add(entry)
                        execs.append(entry)
            except PermissionError:
                # Skip directories we can't read
                continue
        execs = sorted(execs)[:limit]
        return execs
    
    async def _exec_in_sandbox(
        self,
        command: str,
        *,
        exec_dir: Optional[str] = None,
        id: Optional[str] = None,
        async_mode: Optional[bool] = None,
        timeout: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Execute command in the default workspace sandbox via HTTP API.

    Contract aligned with Sandbox REST API:
    - POST {WORKSPACE_SANDBOX_URL|DEFAULT_WORKSPACE_SANDBOX_URL}/v1/shell/exec
    - Request JSON (ShellExecRequest): { id?: string, exec_dir?: string, command: string, async_mode?: boolean, timeout?: number }
    - Response JSON (200): { success: bool, message: string, data: { session_id, command, status, output, console[], exit_code } }
        """
        base = self._get_sandbox_base_url().rstrip("/")
        if not base:
            raise ValueError("WORKSPACE_SANDBOX_URL/DEFAULT_WORKSPACE_SANDBOX_URL is not set; sandbox execution is required")

        url = f"{base}/v1/shell/exec"
        headers: Dict[str, str] = {"Content-Type": "application/json"}

        payload: Dict[str, Any] = {"command": command}
        # ShellExecRequest schema fields
        # - id: optional
        # - exec_dir: optional (working directory, absolute path)
        # - command: required
        # - async_mode: optional (default False)
        # - timeout: optional seconds
        if id is not None:
            payload["id"] = id
        if exec_dir:
            payload["exec_dir"] = exec_dir
        if async_mode is not None:
            payload["async_mode"] = async_mode.lower() == "true"
        if timeout is not None:
            payload["timeout"] = int(float(timeout))

        print(f"[CLI CALL][sandbox] POST {url} command={command!r} exec_dir={exec_dir!r} id={id!r} async_mode={async_mode!r} timeout={timeout!r}")
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(url, json=payload, headers=headers)
        except Exception as e:
            # Network or client error: surface as stderr content, non-zero return code
            return {
                "stdout": "",
                "stderr": f"Sandbox exec request failed: {type(e).__name__}: {e}",
                "returncode": 127,
            }

        # Normalize response strictly as JSON
        status = resp.status_code
        raw_bytes = await resp.aread()
        try:
            body = resp.json()
        except Exception:
            # Requirement: response must be JSON; print and raise
            content_str = raw_bytes.decode(errors="replace")
            print(f"[CLI CALL][sandbox] Non-JSON response (status={status}):\n{content_str}")
            raise RuntimeError("Sandbox exec response is not JSON")

        if 200 <= status < 300:
            data = body.get("data") or {}
            # stdout from 'output' or join console outputs
            stdout = data.get("output")
            if stdout is None and isinstance(data.get("console"), list):
                try:
                    stdout = "\n".join([str(item.get("output", "")) for item in data.get("console", [])])
                except Exception:
                    stdout = ""
            if stdout is None:
                stdout = ""
            # No explicit stderr field in schema; keep empty
            stderr = ""
            rc = data.get("exit_code")
            if rc is None:
                rc = 0
            return {
                "stdout": stdout if isinstance(stdout, str) else str(stdout),
                "stderr": stderr,
                "returncode": int(rc) if isinstance(rc, (int, float)) else 1,
            }
        else:
            # Map common error format (e.g., 422 with 'detail') into stderr
            stderr_msg = body.get("message")
            if not stderr_msg and body.get("detail") is not None:
                try:
                    import json as _json
                    stderr_msg = _json.dumps(body.get("detail"), ensure_ascii=False)
                except Exception:
                    stderr_msg = str(body.get("detail"))
            if not stderr_msg:
                stderr_msg = f"HTTP {status}"
            return {"stdout": "", "stderr": stderr_msg, "returncode": 1}

    def _get_sandbox_base_url(self) -> str:
        """Return sandbox base URL with precedence: WORKSPACE_SANDBOX_URL > DEFAULT_WORKSPACE_SANDBOX_URL."""
        base = os.getenv("WORKSPACE_SANDBOX_URL") or os.getenv("DEFAULT_WORKSPACE_SANDBOX_URL") or ""
        return base
    
    def get_result_validation_hint(self) -> str:
        return (
"""The result is a JSON object with keys: stdout (string), stderr (string), returncode (integer), executed_command (string).
Check for obvious errors in returncode and stderr. If returncode is non-zero, the command likely failed.
If stdout is not empty, check if it is relevant to the task description.""")