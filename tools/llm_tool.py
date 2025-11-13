#!/usr/bin/env python3
"""LLM Tool for Doc Flow Agent
Real OpenAI API implementation

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
import os
import copy
import inspect
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Callable, Tuple
from openai import AsyncOpenAI

from .base_tool import BaseTool


class LLMTool(BaseTool):
    """Large Language Model tool for generating text and structured responses"""

    def __init__(self):
        super().__init__("LLM")
    # Tool always expects a functioning LLM endpoint now (stub mode removed)

        api_key = os.getenv("OPENAI_API_KEY", "")
        base_url = os.getenv("OPENAI_API_BASE", "https://openrouter.ai/api/v1")
        
        self.client = AsyncOpenAI(
            base_url=base_url,
            api_key=api_key
        )
        self.model = os.getenv("OPENAI_MODEL", "openai/gpt-4o-2024-11-20")  

        self.small_model = os.environ.get("OPENAI_SMALL_MODEL", self.model)
        self._call_logger: Optional[Callable[[Dict[str, Any]], None]] = None

    def register_call_logger(self, logger: Optional[Callable[[Dict[str, Any]], None]]) -> None:
        """Register a callback to receive detailed metadata for every LLM invocation."""
        self._call_logger = logger

    async def execute(
        self,
        parameters: Dict[str, Any],
        sop_doc_body: Optional[str] = None,
        *,
        max_retries: int = 0,
        retry_strategies: Optional[List[Any]] = None,
        validators: Optional[List[Callable[[Dict[str, Any]], Any]]] = None,
        retry_llm_tool: Optional['LLMTool'] = None,
    ) -> str:
        """Execute LLM tool with optional retry strategies & validators.

        Backward compatible: if no retry-related args provided, single attempt.
        """

        if not retry_strategies and max_retries == 0:
            return await self._raw_llm_call(parameters)

        base_parameters = copy.deepcopy(parameters)
        retry_tool = retry_llm_tool if retry_llm_tool is not None else self
        last_error: Optional[Exception] = None
        last_response: Optional[Dict[str, Any]] = None

        for strategy in retry_strategies:
            strategy.start(base_parameters)
            total_attempts = max_retries + 1
            for attempt in range(1, total_attempts + 1):
                attempt_params = await strategy.build_attempt_parameters(
                    base_parameters=base_parameters,
                    attempt_index=attempt,
                    last_response=last_response,
                    last_error=last_error,
                )

                response = await retry_tool.execute(
                    attempt_params,
                    sop_doc_body=sop_doc_body,
                    max_retries=0,
                    retry_strategies=None,
                    validators=None,
                    retry_llm_tool=retry_llm_tool,
                )

                try:
                    for v in validators:
                        res = v(response)
                        if inspect.isawaitable(res):
                            await res
                    return response
                except Exception as ve:
                    last_error = ve
                    last_response = response
                    print(f"[LLM RETRY] Validation failed (strategy={strategy.name()} attempt={attempt}/{total_attempts}): {ve}")
                    continue

        if last_error:
            raise last_error
        return await self._raw_llm_call(parameters)

    async def _raw_llm_call(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Internal single-attempt LLM invocation (original execute core)."""
        self.validate_parameters(parameters, ['prompt'])
        prompt = parameters.get('prompt', '')
        tools = parameters.get('tools', None)
        max_tokens = parameters.get('max_tokens', 20000)

        call_start_time = self._current_time()

        print(f"[LLM CALL] Prompt: {prompt}...")
        if tools:
            print(f"[LLM CALL] Tools provided: {[tool.get('function', {}).get('name', 'unknown') for tool in tools]}")

        call_model = parameters.get('model', self.model)
        api_params = {
            "model": call_model,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "max_completion_tokens": max_tokens,
            "stream": True,
        }
        if tools:
            api_params["tools"] = tools

        stream = await self.client.chat.completions.create(**api_params)
        content, tool_calls, token_usage = await self._collect_streaming_chunks_with_tools(stream)
        call_end_time = self._current_time()

        self._emit_call_log(
            prompt=prompt,
            response=content,
            model=call_model,
            tool_calls=tool_calls,
            token_usage=token_usage,
            start_time=call_start_time,
            end_time=call_end_time,
            all_parameters=parameters
        )

        if tools and not tool_calls:
            print("[LLM FALLBACK] No native tool calls returned. Attempting XML JSON fallback.")
            fallback_prompt = prompt + self._build_fallback_tool_instructions(tools)
            api_params_fallback = dict(api_params)
            api_params_fallback["messages"] = [
                {"role": "user", "content": fallback_prompt}
            ]
            api_params_fallback["tools"] = None
            print(f"[LLM FALLBACK] New Prompt: \n-----{fallback_prompt}...")
            # Re-issue call
            fallback_start_time = self._current_time()
            stream_fb = await self.client.chat.completions.create(**api_params_fallback)
            content_fb, _, fb_usage = await self._collect_streaming_chunks_with_tools(stream_fb)
            fallback_end_time = self._current_time()
            parsed_calls = self._parse_xml_wrapped_tool_json(content_fb, tools)
            if parsed_calls:
                print(f"[LLM FALLBACK] Parsed {len(parsed_calls)} tool call(s) from XML fallback.")
                content = content_fb
                tool_calls = parsed_calls
                token_usage = fb_usage
            else:
                print("[LLM FALLBACK] Failed to parse XML fallback output.")
                # Even if parsing failed, keep the raw content for logging visibility
                content = content_fb
                tool_calls = []
                token_usage = fb_usage

            self._emit_call_log(
                prompt=fallback_prompt,
                response=content,
                model=call_model,
                tool_calls=tool_calls,
                token_usage=token_usage,
                start_time=fallback_start_time,
                end_time=fallback_end_time,
                all_parameters=parameters
            )

        print(f"[LLM RESPONSE] {content[:100]}...")
        if tool_calls:
            print(f"[TOOL CALLS] Collected {len(tool_calls)} tool calls:")
            for tool_call in tool_calls:
                print(f"  - Tool: {tool_call.get('name', 'unknown')}")
                print(f"    Arguments: {tool_call.get('arguments', {})}")
        return {
            "content": content,
            "tool_calls": tool_calls,
        }

    def _current_time(self) -> str:
        """Consistent UTC timestamp used for tracing metadata."""
        return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    # ---------------- Fallback Tool Call Support (XML-wrapped JSON) -----------------
    def _build_fallback_tool_instructions(self, tools: Any) -> str:
        """Builds instructions appended to the original prompt to coerce models lacking
        native tool-call support to emit a JSON arguments object wrapped in an XML tag
        named after the function.

        Format per tool (only first tool currently supported in fallback):
        <function_name>{"param":"value", ...}</function_name>

        Args:
            tools: Original tools schema list passed to execute().

        Returns:
            Instruction string to append to user prompt.
        """
        if not tools:
            return ""
        if not isinstance(tools, (list, tuple)):
            return ""
        if len(tools) == 0:
            return ""
        first = tools[0]
        fn = first.get("function", {}) if isinstance(first, dict) else {}
        fn_name = fn.get("name", "tool_function")
        params = fn.get("parameters", {})
        # Build a concise schema description for guidance
        schema_desc = json.dumps(params, ensure_ascii=False, indent=2)
        return (
            "\n\n--- RETURN FORMAT INSTRUCTIONS ---\n"
            "Return exactly ONE XML block whose tag name is the function name. Inside the tag, put a single JSON object with keys matching the parameters schema.\n"
            f"Function name: {fn_name}\n"
            "JSON Schema (for guidance only):\n"
            f"{schema_desc}\n"
            "Output format (no extra text, no markdown, no explanation):\n"
            f"<{fn_name}>{{}} </{fn_name}> where {{}} is the JSON arguments object.\n"
            "Do NOT wrap output in markdown fences. Do NOT include commentary. Just the XML element."
        )

    def _parse_xml_wrapped_tool_json(self, content: str, tools: Any):
        """Parse fallback XML-wrapped JSON tool call outputs.

        Looks for pattern: <function_name>{json}</function_name>
        Only supports the first tool definition (consistent with builder).

        Args:
            content: Raw model text output.
            tools: Original tools schema list (to know function name).

        Returns:
            List with a single tool_call dict or empty list if not found / parse error.
        """
        if not tools or not isinstance(tools, (list, tuple)) or len(tools) == 0:
            print("[FALLBACK PARSE ERROR] No tools provided for parsing.")
            return []
        first = tools[0]
        fn = first.get("function", {}) if isinstance(first, dict) else {}
        fn_name = fn.get("name", "tool_function")
        if not content or fn_name not in content:
            print(f"[FALLBACK PARSE ERROR] Function name '{fn_name}' not found in content: \n---{content}\n---")
            return []
        import re
        pattern = rf"<\s*{re.escape(fn_name)}\s*>(.*?)<\s*/\s*{re.escape(fn_name)}\s*>"
        match = re.search(pattern, content, flags=re.DOTALL | re.IGNORECASE)
        if not match:
            print(f"[FALLBACK PARSE ERROR] No matching XML tags found for function '{fn_name}' in content.")
            return []
        inner = match.group(1).strip()
        # Some models may include code fences or stray tags, sanitize minimally
        if inner.startswith('```'):
            inner = inner.strip('`')
        # Attempt JSON parse
        try:
            args = json.loads(inner)
        except json.JSONDecodeError:
            print(f"[FALLBACK PARSE ERROR] Failed to parse JSON from XML-wrapped content: {inner}")
            return []
        if not isinstance(args, dict):
            print(f"[FALLBACK PARSE ERROR] Parsed arguments is not a JSON object: {args}")
            return []
        return [{
            'id': 'fallback_xml_0',
            'name': fn_name,
            'arguments': args
        }]

    # Public helper for tests
    def parse_tool_call_from_content(self, content: str, tools: Any):
        """Public wrapper around internal XML fallback parser for unit testing.

        Args:
            content: Model output text.
            tools: Tools schema list.

        Returns:
            Parsed tool_calls list (possibly empty).
        """
        return self._parse_xml_wrapped_tool_json(content, tools)
    
    def _is_valid_chunk_with_content(self, chunk) -> bool:
        """Check if chunk has valid choices and content
        
        Args:
            chunk: Response chunk from OpenAI API
            
        Returns:
            True if chunk has valid content, False otherwise
        """
        return (hasattr(chunk, 'choices') and 
                len(chunk.choices) > 0 and 
                hasattr(chunk.choices[0], 'delta') and 
                hasattr(chunk.choices[0].delta, 'content') and 
                chunk.choices[0].delta.content is not None)
    
    async def _collect_streaming_chunks_with_tools(self, stream) -> Tuple[str, List[Dict[str, Any]], Optional[Dict[str, Any]]]:
        """Collect and combine streaming response chunks with optional tool call handling
        
        Args:
            stream: Async stream from OpenAI API
            
        Returns:
            Tuple of (combined content string, list of tool calls)
        """
        content_chunks: List[str] = []
        tool_calls: List[Dict[str, Any]] = []
        tool_call_chunks: Dict[int, Dict[str, Any]] = {}  # Track partial tool calls by index
        token_usage: Optional[Dict[str, Any]] = None
        
        async for chunk in stream:
            if not hasattr(chunk, 'choices') or len(chunk.choices) == 0:
                continue
                
            choice = chunk.choices[0]
            delta = choice.delta if hasattr(choice, 'delta') else None
            
            if not delta:
                continue
            
            # Handle content chunks
            if hasattr(delta, 'content') and delta.content is not None:
                content_chunks.append(delta.content)
            
            # Handle tool call chunks
            if hasattr(delta, 'tool_calls') and delta.tool_calls is not None:
                for tool_call_chunk in delta.tool_calls:
                    if not hasattr(tool_call_chunk, 'index'):
                        continue
                        
                    index = tool_call_chunk.index
                    
                    # Initialize tool call tracking for this index
                    if index not in tool_call_chunks:
                        tool_call_chunks[index] = {
                            'id': '',
                            'type': 'function',
                            'function': {
                                'name': '',
                                'arguments': ''
                            }
                        }
                    
                    # Update tool call ID
                    if hasattr(tool_call_chunk, 'id') and tool_call_chunk.id:
                        tool_call_chunks[index]['id'] = tool_call_chunk.id
                    
                    # Update function details
                    if hasattr(tool_call_chunk, 'function') and tool_call_chunk.function:
                        func_chunk = tool_call_chunk.function
                        if hasattr(func_chunk, 'name') and func_chunk.name:
                            tool_call_chunks[index]['function']['name'] += func_chunk.name
                        if hasattr(func_chunk, 'arguments') and func_chunk.arguments:
                            tool_call_chunks[index]['function']['arguments'] += func_chunk.arguments
            # Capture token usage when the API provides it (typically final chunk)
            chunk_usage = getattr(chunk, 'usage', None)
            if chunk_usage:
                if isinstance(chunk_usage, dict):
                    candidate = {
                        k: chunk_usage.get(k)
                        for k in ('prompt_tokens', 'completion_tokens', 'total_tokens')
                        if chunk_usage.get(k) is not None
                    }
                    if candidate:
                        token_usage = candidate
                else:
                    candidate = {
                        key: getattr(chunk_usage, key)
                        for key in ('prompt_tokens', 'completion_tokens', 'total_tokens')
                        if getattr(chunk_usage, key, None) is not None
                    }
                    if candidate:
                        token_usage = candidate
        
        # Process completed tool calls
        for tool_call in tool_call_chunks.values():
            if tool_call['function']['name']:  # Only add if we have a function name
                try:
                    # Parse the arguments JSON
                    arguments = json.loads(tool_call['function']['arguments']) if tool_call['function']['arguments'] else {}
                    tool_calls.append({
                        'id': tool_call['id'],
                        'name': tool_call['function']['name'],
                        'arguments': arguments
                    })
                except json.JSONDecodeError as e:
                    print(f"[TOOL CALL ERROR] Failed to parse arguments: {e}")
                    print(f"Raw arguments: {tool_call['function']['arguments']}")
        
        # Combine all content chunks into final content
        return ''.join(content_chunks), tool_calls, token_usage

    def _emit_call_log(self, prompt: str, response: str, model: str, tool_calls: List[Dict[str, Any]],
                       token_usage: Optional[Dict[str, Any]], start_time: str, end_time: str,
                       all_parameters: Dict[str, Any]) -> None:
        """Send a structured event to the registered call logger, if present."""
        if not self._call_logger:
            return
        payload = {
            "prompt": prompt,
            "response": response,
            "model": model,
            "tool_calls": tool_calls,
            "token_usage": token_usage,
            "start_time": start_time,
            "end_time": end_time,
            "all_parameters": all_parameters,
        }
        try:
            self._call_logger(payload)
        except Exception as exc:  # pragma: no cover - best-effort logging
            print(f"[LLM CALL LOG] Warning: failed to emit call log: {exc}")
    
    async def _test_connection(self) -> bool:
        """Test connection to the API endpoint"""
        # In integration test MOCK mode, skip connection test to keep deterministic hash/prompt behavior
        if os.getenv("INTEGRATION_TEST_MODE", "").lower() == "mock":
            return True
        try:
            stream = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": "test"}],
                max_tokens=2,
                stream=True,
            )
            # Just collect the chunks to verify streaming works
            # We only need the content, ignore tool calls for connection testing
            _, _, _ = await self._collect_streaming_chunks_with_tools(stream)
            return True
        except Exception as e:
            print(f"[LLM CONNECTION ERROR] {str(e)}")
            # print stack trace for debugging
            import traceback
            traceback.print_exc()
            return False

    def get_result_validation_hint(self) -> str:
        return "The result is a JSON object with keys: content (string), tool_calls (array of tool call objects). Check for obvious rejection for answer the prompt or truncate the result due to max tokens. If the current task requirement is not satisfied, generate a new task like `Follow llm.md to xxxx` which is using llm.md to fix the error or complete the remaining work."

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    # Write a simple demo for this tool
    async def demo():
        llm_tool = LLMTool()
        
        # Test basic functionality
        response = await llm_tool.execute({"prompt": "Hello, world!"})
        print(f"LLM Response: {response}")
        
        # Test with tool schema
        print("\n" + "="*50)
        print("Testing with tool schema:")
        print("="*50 + "\n")
        
        new_task_list_tool = {
            "type": "function",
            "function": {
                "name": "new_task_list",
                "description": "Create a new task list with specified items",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "tasks": {
                            "type": "array",
                            "items": {
                                "type": "string"
                            },
                            "description": "List of task strings"
                        }
                    },
                    "required": ["tasks"]
                }
            }
        }
        
        tool_response = await llm_tool.execute({
            "prompt": "Create a task list for planning a weekend camping trip. Use the new_task_list tool.",
            "tools": [new_task_list_tool]
        })
        print(f"Tool Response: {tool_response}")

    asyncio.run(demo())
    # Provide cli example:
    # python -m doc_flow_agent.tools.llm_tool
