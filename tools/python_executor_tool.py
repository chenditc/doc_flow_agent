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
from typing import Any, Dict, Optional, List, Tuple
import os
import sys
from importlib import metadata as importlib_metadata
import asyncio

import httpx
from utils.sandbox import get_sandbox_base_url

from dotenv import load_dotenv
from tools.base_tool import BaseTool
from tools.llm_tool import LLMTool
from tools.retry_strategies import SimpleRetryStrategy, AppendValidationHintStrategy

# Load environment variables from .env file
load_dotenv()


class PythonExecutorTool(BaseTool):
    def __init__(self, llm_tool: LLMTool, max_generation_attempts: int = 3):
        super().__init__("PYTHON_EXECUTOR")
        if max_generation_attempts < 1:
            raise ValueError("max_generation_attempts must be at least 1")

        self.llm_tool = llm_tool
        self.max_generation_attempts = max_generation_attempts
        # Sandbox base URL (shared precedence and default via utils)
        self.sandbox_base_url = get_sandbox_base_url()
        # Timeout configuration (centralized, env-overridable)
        self.TIMEOUT_MIN = 1
        self.TIMEOUT_MAX = 6000
        self.DEFAULT_TIMEOUT = self.TIMEOUT_MAX 

    def _clamp_timeout(self, value: int) -> int:
        return min(max(value, self.TIMEOUT_MIN), self.TIMEOUT_MAX)

    async def execute(self, parameters: Dict[str, Any], sop_doc_body: str = "", doc_path: str = "") -> Dict[str, Any]:
        task_description = parameters.get("task_description")
        related_context_content = parameters.get("related_context_content", {})
        # preferred timeout (seconds): default from self.DEFAULT_TIMEOUT; clamp to [TIMEOUT_MIN, TIMEOUT_MAX]
        preferred_timeout: Optional[int] = parameters.get("timeout", self.DEFAULT_TIMEOUT)

        python_code = parameters.get("python_code")
        if not python_code:
            tool_schema = self._create_python_code_tool_schema()

            sop_guidance = ""
            if sop_doc_body.strip() == "":
                sop_doc_body = "No special guidance, follow the instruction from user."

            # Wrap SOP content with an informative tag including the document path when available
            tag_name = doc_path.strip() if doc_path and doc_path.strip() != "" else "sop_document"
            sop_guidance = (
                f"<Document Content>\n"
                f"<{tag_name}>\n"
                f"{sop_doc_body.strip()}\n"
                f"</{tag_name}>\n"
                f"</Document Content>\n"
            )

            # Fetch available libs from sandbox env (fallback to local if fails)
            available_libs = await self._get_available_python_libraries_from_sandbox()
            if not available_libs:
                available_libs = self._get_available_python_libraries()
            prompt = f"""
You are a Python code generation assistant.
Your task is to write a single Python function named `process_step` that takes one argument: `context: {type(related_context_content).__name__}`.
This function will be executed to perform following specific task. Import necessary library if you used any.
The context object will contain all the necessary data. The json serialized context object has been attached here for you to understand the input data structure.

Requirements:
 - The function should return a JSON-serializable value.
 - Do not catch exceptions; let them propagate.
 - Print any necessary debug information to stdout.
 - Also propose an integer timeout (in seconds) named `timeout` for how long this function may take to run based on the task complexity ({self.TIMEOUT_MIN}..{self.TIMEOUT_MAX}).

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

            # Validator for code extraction & compilation
            def parse_and_validate_code(resp: Dict[str, Any]):
                candidate_code, _ = self._extract_code_and_timeout_from_response(resp)
                if not isinstance(candidate_code, str):
                    candidate_code = str(candidate_code)
                compile(candidate_code, "<generated_code>", "exec")
                return candidate_code

            response = await self.llm_tool.execute(
                {
                    "prompt": prompt,
                    "temperature": 0.0,
                    "tools": [tool_schema],
                },
                max_retries=self.max_generation_attempts - 1,
                validators=[parse_and_validate_code],
                retry_strategies=[
                    AppendValidationHintStrategy(),
                ],
                retry_llm_tool=self.llm_tool,
            )
            # Extract code and suggested timeout
            python_code, final_timeout = self._extract_code_and_timeout_from_response(response)
            final_timeout = self._clamp_timeout(final_timeout)
        else:
            if not isinstance(python_code, str):
                python_code = str(python_code)
            final_timeout = self._clamp_timeout(preferred_timeout)

        # Use sandbox: upload context to /tmp, execute wrapped code, download result
        run_id = uuid.uuid4()
        sandbox_context_path = f"/tmp/context_{run_id}.json"
        sandbox_output_path = f"/tmp/result_{run_id}.json"

        # Upload context JSON
        await self._sandbox_upload_json(sandbox_context_path, related_context_content)

        # Build wrapped code (user code + wrapper to read context, call, and write result)
        wrapped_code = self._build_wrapper_code(python_code, sandbox_context_path, sandbox_output_path)
        # Compile wrapped code to catch syntax errors early
        compile(wrapped_code, "<wrapped_code>", "exec")

        # Execute in sandbox
        exec_resp = await self._sandbox_execute_code(wrapped_code, timeout=final_timeout)
        # Collect stdout/stderr from sandbox response outputs:
        # For each element in outputs, if output_type == 'error' -> stderr; otherwise -> stdout.
        process_stdout, process_stderr = self._collect_streams_from_exec_resp(exec_resp)
        exec_status = exec_resp.get("status")

        # Derive exception from exec_resp outputs (prefer traceback)
        exception_details = self._extract_exception_from_exec_resp(exec_resp)

        # Download result JSON (only contains return_value now; wrapper no longer writes exception)
        result_data = await self._sandbox_download_json(sandbox_output_path)
        if result_data is None:
            # If sandbox indicates error via exec_resp, rely on that; otherwise note missing file
            if not exception_details:
                exception_details = f"Output file not found in sandbox: {sandbox_output_path}"
            return_value = None
        else:
            return_value = result_data.get("return_value")

        return {
            "python_code": python_code,
            "return_value": return_value,
            "stdout": process_stdout,
            "stderr": process_stderr,
            "exception": exception_details,
        }

    @staticmethod
    def _collect_streams_from_exec_resp(exec_resp: Dict[str, Any]) -> Tuple[str, str]:
        """Parse sandbox exec response to collect stdout and stderr.

        Rules:
        - If an output element has output_type == 'error', its content goes to stderr
        - Otherwise, its textual content goes to stdout
        - If no outputs-derived text was found, fall back to top-level stdout/stderr fields
        """
        stdout, stderr, _ = PythonExecutorTool._parse_streams_and_exception(exec_resp)
        return stdout, stderr

    @staticmethod
    def _extract_exception_from_exec_resp(exec_resp: Dict[str, Any]) -> Optional[str]:
        """Extract exception information from sandbox exec response.

        Returns traceback (preferred) or ename/evalue if available, else None.
        """
        _, _, exc = PythonExecutorTool._parse_streams_and_exception(exec_resp)
        return exc

    @staticmethod
    def _parse_streams_and_exception(exec_resp: Dict[str, Any]) -> Tuple[str, str, Optional[str]]:
        """Single-pass parse of outputs to produce stdout, stderr, and exception string.

        - Non-error outputs contribute to stdout (text > data['text/plain'] > json(data)).
        - Error outputs contribute to stderr; first error also sets exception:
          prefer joined traceback; else "ename: evalue"; else None.
        - If stdout/stderr empty, fallback to top-level fields.
        """
        try:
            outputs = exec_resp.get("outputs") or []
        except Exception:
            outputs = []

        stdout_parts: List[str] = []
        stderr_parts: List[str] = []
        exception_text: Optional[str] = None

        for out in outputs:
            if not isinstance(out, dict):
                stdout_parts.append(str(out))
                continue
            otype = out.get("output_type") or out.get("type")
            if otype == "error":
                tb = out.get("traceback")
                if isinstance(tb, list) and tb:
                    tb_text = "\n".join([str(x) for x in tb])
                    stderr_parts.append(tb_text)
                    if exception_text is None:
                        exception_text = tb_text.strip()
                else:
                    ename = out.get("ename")
                    evalue = out.get("evalue")
                    msg_bits = [str(x) for x in [ename, evalue] if x]
                    if msg_bits:
                        msg = ": ".join(msg_bits)
                        stderr_parts.append(msg)
                        if exception_text is None:
                            exception_text = msg
                    else:
                        try:
                            dumped = json.dumps(out, ensure_ascii=False)
                        except Exception:
                            dumped = str(out)
                        stderr_parts.append(dumped)
                        if exception_text is None:
                            exception_text = dumped
            else:
                text = out.get("text")
                if isinstance(text, list):
                    text = "".join([str(x) for x in text])
                if not text:
                    data = out.get("data")
                    if isinstance(data, dict):
                        if "text/plain" in data:
                            tp = data.get("text/plain")
                            if isinstance(tp, list):
                                tp = "".join([str(x) for x in tp])
                            text = str(tp)
                        else:
                            try:
                                text = json.dumps(data, ensure_ascii=False)
                            except Exception:
                                text = str(data)
                if text is None:
                    text = ""
                stdout_parts.append(str(text))

        stdout = "".join(stdout_parts).strip()
        stderr = "\n".join(stderr_parts).strip()

        if not stdout:
            top_stdout = exec_resp.get("stdout")
            if top_stdout:
                stdout = str(top_stdout)
        if not stderr:
            top_stderr = exec_resp.get("stderr")
            if top_stderr:
                stderr = str(top_stderr)

        return stdout, stderr, (exception_text.strip() if isinstance(exception_text, str) else exception_text)

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
                        "code": {
                            "type": "string",
                            "description": "Complete Python function definition for function `process_step` that performs the requested task"
                        },
                        "timeout": {
                            "type": "integer",
                            "description": f"Suggested timeout seconds for executing the code ({self.TIMEOUT_MIN}..{self.TIMEOUT_MAX})",
                            "minimum": self.TIMEOUT_MIN,
                            "maximum": self.TIMEOUT_MAX
                        }
                    },
                    "required": ["code"]
                }
            }
        }
        
        return tool_schema

    def _extract_code_and_timeout_from_response(self, response) -> Tuple[str, Optional[int]]:
        """Extract Python code and suggested timeout from LLM response with tool calls
        
        Args:
            response: LLM response containing tool calls
            
        Returns:
            (code: str, timeout: Optional[int])
        """

        # Extract tool calls from response
        tool_calls = response.get("tool_calls", [])
        if not tool_calls:
            raise ValueError("No tool call in LLM response")
        
        # Get the first (and should be only) tool call
        tool_call = tool_calls[0]
        if tool_call.get("name") != "generate_python_code":
            raise ValueError(f"Unexpected tool call: {tool_call.get('name')}")
        
        # Extract arguments
        arguments = tool_call.get("arguments", {})
        python_code = arguments.get("code")
        suggested_timeout = arguments.get("timeout")
        
        if not python_code:
            raise ValueError("No Python code generated by LLM")
        
        try:
            if suggested_timeout is not None:
                suggested_timeout = int(suggested_timeout)
        except Exception:
            suggested_timeout = self.DEFAULT_TIMEOUT
            
        return python_code, suggested_timeout

    # Backward-compatible shim for older tests expecting only code extraction
    def _extract_python_code_from_response(self, response) -> str:
        code, _ = self._extract_code_and_timeout_from_response(response)
        if not isinstance(code, str):
            return str(code)
        return code

    def get_result_validation_hint(self) -> str:
        return "The result is a JSON object with keys: python_code (string), return_value (any), stdout (string), stderr (string), exception (string or null). Check for obvious errors in exception and stderr. If exception is not null, the code execution failed. Ensure return_value is relevant to the task description and satisfies task requirements."

    async def _get_available_python_libraries_from_sandbox(self, limit: int = 300) -> str:
        """Query the sandbox to get available top-level libraries (distribution names).

        Returns a newline-separated list. On failure returns empty string.
        """
        list_code = f"""
from importlib import metadata as importlib_metadata
import json
names = []
try:
    for d in importlib_metadata.distributions():
        name = d.metadata.get("Name") or d.metadata.get("Summary") or ""
        if not name:
            continue
        name = name.strip()
        if (not name) or name.startswith(("_", "python-")) or name.endswith(".dist-info"):
            continue
        names.append(name)
    seen = set()
    unique = []
    for n in names:
        k = n.lower()
        if k in seen:
            continue
        seen.add(k)
        unique.append(n)
    unique = sorted(unique, key=lambda x: x.lower())[:{limit}]
    print(json.dumps(unique, ensure_ascii=False))
except Exception:
    print("[]")
"""
        try:
            resp = await self._sandbox_execute_code(list_code, timeout=30)
            stdout = resp.get("stdout")
            if not stdout:
                return ""
            libs = json.loads(stdout)
            if not isinstance(libs, list):
                return ""
            libs = [str(x) for x in libs][:limit]
            return "\n".join(libs)
        except Exception:
            return ""

    def _build_wrapper_code(self, user_code: str, context_path: str, output_path: str) -> str:
        """Build a wrapper script that loads context, calls process_step, and writes result JSON.

        The output file will contain: {"return_value": Any, "exception": str|None}
        """
        wrapper = """
{user_code}

import json, traceback

def __doc_flow_agent_execute():
    _ctx = "{context_path}"
    _out = "{output_path}"

    with open(_ctx, "r") as f:
        context = json.load(f)
    rv = process_step(context)
    result = {{"return_value": rv, "exception": None}}

    with open(_out, "w") as f:
        json.dump(result, f, ensure_ascii=False)

__doc_flow_agent_execute()
""".format(context_path=context_path, output_path=output_path, user_code=user_code)
        return wrapper

    async def _sandbox_upload_json(self, path: str, content: Dict[str, Any]) -> str:
        """Upload JSON content to sandbox at the specified absolute path (e.g., /tmp/...).

        Returns the server-side file path.
        """
        url = f"{self.sandbox_base_url}/v1/file/upload"
        data = {"path": path}
        json_bytes = json.dumps(content, ensure_ascii=False).encode("utf-8")
        files = {"file": (os.path.basename(path) or "context.json", json_bytes, "application/json")}
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, data=data, files=files)
            resp.raise_for_status()
            body = resp.json()
            # Expecting { success: bool, data: { file_path: str, file_size: int, success: bool } }
            server_path = None
            if isinstance(body, dict):
                data_obj = body.get("data") or body
                if isinstance(data_obj, dict):
                    server_path = data_obj.get("file_path") or data_obj.get("path")
            return server_path or path

    async def _sandbox_download_json(self, path: str) -> Optional[Dict[str, Any]]:
        """Download JSON file from sandbox path. Returns dict or None if not found/failed."""
        url = f"{self.sandbox_base_url}/v1/file/download"
        params = {"path": path}
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, params=params)
            if resp.status_code != 200:
                return None
            # Some servers return bytes directly; assume JSON content
            try:
                return resp.json()
            except Exception:
                try:
                    return json.loads(resp.content.decode("utf-8", errors="ignore"))
                except Exception:
                    return None

    async def _sandbox_execute_code(self, code: str, timeout: int) -> Dict[str, Any]:
        """Execute code in sandbox via unified runtime and return the inner data object.

        Returns a dict like CodeExecuteResponse (language/status/outputs/code/stdout/stderr/exit_code)
        wrapped in the server's generic Response.

        Example failed response: {'success': False, 'message': 'Python execution error', 'data': {'language': 'python', 'status': 'error', 'outputs': [{'output_type': 'error', 'name': None, 'text': None, 'data': None, 'metadata': {}, 'execution_count': None, 'ename': 'SyntaxError', 'evalue': 'unterminated f-string literal (detected at line 31) (3660732828.py, line 31)', 'traceback': ['  \x1b[36mCell\x1b[39m\x1b[36m \x1b[39m\x1b[32mIn[1]\x1b[39m\x1b[32m, line 31\x1b[39m\n\x1b[31m    \x1b[39m\x1b[31mresult = {"return_value": None, "exception": f"{e.__class__.__name__}: {e}\x1b[39m\n                                                 ^\n\x1b[31mSyntaxError\x1b[39m\x1b[31m:\x1b[39m unterminated f-string literal (detected at line 31)\n']}], 'code': '....
        """
        url = f"{self.sandbox_base_url}/v1/code/execute"
        payload = {"language": "python", "code": code, "timeout": timeout}
        async with httpx.AsyncClient() as client:
            print(f"Executing code in sandbox... {url}")
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            body = resp.json()
            print(f"Sandbox execution response: {body}")
            if isinstance(body, dict):
                data_obj = body.get("data") or {}
                if isinstance(data_obj, dict):
                    return data_obj
            return {}