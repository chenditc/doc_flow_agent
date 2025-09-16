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
from typing import Dict, Any
from openai import AsyncOpenAI

from .base_tool import BaseTool


class LLMTool(BaseTool):
    """Large Language Model tool for generating text and structured responses"""

    def __init__(self):
        super().__init__("LLM")
        # Initialize OpenAI client with custom endpoint
        self.offline_mode = os.getenv("LLM_OFFLINE_MODE", "0") in ("1", "true", "True")
        if self.offline_mode:
            # Provide deterministic stub behavior
            self.client = None  # type: ignore
            self.model = "offline-stub"
            print("[LLM INIT] Running in OFFLINE stub mode – no external API calls will be made.")
        else:
            api_key = os.getenv("OPENAI_API_KEY", "")
            base_url = os.getenv("OPENAI_API_BASE", "https://openrouter.ai/api/v1")
            if "cognitiveservices.azure.com" in base_url and not api_key:
                api_key = self.create_azure_token_provider()
                print("[LLM INIT] Using Azure OpenAI endpoint")

            self.client = AsyncOpenAI(
                base_url=base_url,
                api_key=api_key
            )
            self.model = os.getenv("OPENAI_MODEL", "openai/gpt-4o-2024-11-20")   
    
    def create_azure_token_provider(self):
        from azure.identity.aio import DefaultAzureCredential, get_bearer_token_provider

        token_provider = get_bearer_token_provider(
            DefaultAzureCredential(), "https://cognitiveservices.azure.com/.default"
        )
        return token_provider

    async def execute(self, parameters: Dict[str, Any]) -> str:
        """Execute LLM tool with given parameters
        
        Args:
            parameters: Dictionary containing 'prompt', optional 'tools' schema, and other parameters
            
        Returns:
            JSON string with LLM response
        """
        if not self.offline_mode:
            if not await self._test_connection():
                raise RuntimeError("Failed to connect to LLM API")
        
        prompt = parameters.get('prompt', '')
        tools = parameters.get('tools', None)
        max_tokens = parameters.get('max_tokens', 20000)
        
        # Log the prompt being sent
        print(f"[LLM CALL] Prompt: {prompt}...")
        if tools:
            print(f"[LLM CALL] Tools provided: {[tool.get('function', {}).get('name', 'unknown') for tool in tools]}")
        
        if self.offline_mode:
            # Produce deterministic pseudo-response for tests (no randomness)
            # Respect a simple convention: if tools provided, emit a tool call structure.
            # Special handling: JSON path generator expects a python code block in response.
            if "Please select the most appropriate SOP document" in prompt:
                # Heuristic: if prompt contains 'bash' choose tools/bash, else fallback
                chosen_doc = "tools/bash" if "bash" in prompt.lower() else "general/fallback"
                content = (
                    f"[OFFLINE LLM STUB RESPONSE]\nPrompt hash: {abs(hash(prompt)) % 10000}\n"
                    f"<doc_id>{chosen_doc}</doc_id>"
                )
            elif "Generate Parameter Extraction Code" in prompt:
                # Provide minimal valid structure with code block for regex extraction.
                content = (
                    "[OFFLINE LLM STUB RESPONSE]\n"
                    + f"Prompt hash: {abs(hash(prompt)) % 10000}\n"
                    + "<THINK_PROCESS>\nThis is a deterministic offline reasoning step.\n</THINK_PROCESS>\n"
                    + "<GENERATED_CODE>\n```python\ndef extract_func(context):\n    # Offline stub returns original task description if present\n    return context.get('current_task', '<NOT_FOUND_IN_CANDIDATES>')\n```\n</GENERATED_CODE>\n"
                )
            elif "You MUST use the generate_output_path tool" in prompt or "generate_output_path tool" in prompt:
                # Provide a deterministic tool call output path
                content = (
                    f"[OFFLINE LLM STUB RESPONSE]\nPrompt hash: {abs(hash(prompt)) % 10000}\n"
                    "Deciding output path..."
                )
                tool_calls = [{
                    "id": "offline_tool_call_0",
                    "name": "generate_output_path",
                    "arguments": {"output_path": "$.cli_output"}
                }]
                return {"content": content, "tool_calls": tool_calls}
            elif "extract any new task descriptions" in prompt.lower() or "extract_new_tasks" in prompt:
                # Return empty task list via tool call
                content = (
                    f"[OFFLINE LLM STUB RESPONSE]\nPrompt hash: {abs(hash(prompt)) % 10000}\nNo follow-up tasks."
                )
                tool_calls = [{
                    "id": "offline_tool_call_0",
                    "name": "extract_new_tasks",
                    "arguments": {"tasks": []}
                }]
                return {"content": content, "tool_calls": tool_calls}
            else:
                # Heuristic content generation for common test prompts
                lowered = prompt.lower()
                if "calculate the area of a circle" in lowered or "calculate_circle_area" in lowered:
                    content = (
                        f"[OFFLINE LLM STUB RESPONSE]\nPrompt hash: {abs(hash(prompt)) % 10000}\n"
                        "```python\n"
                        "import math\n"
                        "def calculate_circle_area(radius: float) -> float:\n"
                        "    return math.pi * radius * radius\n"
                        "```\n"
                    )
                else:
                    content = f"[OFFLINE LLM STUB RESPONSE]\nPrompt hash: {abs(hash(prompt)) % 10000}\n{prompt[:200]}"  # keep it short
            tool_calls = []
            if tools:
                # Create minimal tool call echoing first tool name
                first_tool = tools[0]["function"]["name"] if tools else "unknown_tool"
                arguments: Dict[str, Any] = {}
                if first_tool == "generate_command":
                    import re as _re
                    # Find all cat occurrences followed by a non-space token
                    matches = _re.findall(r"cat\s+([^\s]+)", prompt)
                    chosen = None
                    for m in matches:
                        # Prefer a real path token containing a dot or slash
                        if m.startswith("./") or m.startswith("/") or "." in m:
                            chosen = m.strip("'\":)")  # strip quotes / parens / colon but keep leading dot
                            break
                    if not chosen and matches:
                        chosen = matches[-1].strip("'\":)")
                    if chosen:
                        # Remove trailing punctuation that might break the command
                        chosen = chosen.rstrip("'\".,")
                        arguments["command"] = f"cat {chosen}"
                elif first_tool == "generate_output_path":
                    arguments["output_path"] = "$.output"
                tool_calls = [{
                    "id": "offline_tool_call_0",
                    "name": first_tool,
                    "arguments": arguments
                }]
        else:
            # Prepare API call parameters
            api_params = {
                "model": self.model,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "max_completion_tokens": max_tokens,
                "stream": True,
            }
            
            # Add tools if provided
            if tools:
                api_params["tools"] = tools
                api_params["tool_choice"] = "required"
            
            # Make streaming OpenAI API call
            stream = await self.client.chat.completions.create(**api_params)
            
            # Collect streaming response chunks and tool calls
            content, tool_calls = await self._collect_streaming_chunks_with_tools(stream)

        print(f"[LLM RESPONSE] {content[:100]}...")
        if tool_calls:
            print(f"[TOOL CALLS] Collected {len(tool_calls)} tool calls:")
            for tool_call in tool_calls:
                print(f"  - Tool: {tool_call.get('name', 'unknown')}")
                print(f"    Arguments: {tool_call.get('arguments', {})}")
        
        # Return tool calls if available, otherwise just content
        return {
            "content": content,
            "tool_calls": tool_calls
        }
    
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
    
    async def _collect_streaming_chunks_with_tools(self, stream):
        """Collect and combine streaming response chunks with optional tool call handling
        
        Args:
            stream: Async stream from OpenAI API
            
        Returns:
            Tuple of (combined content string, list of tool calls)
        """
        content_chunks = []
        tool_calls = []
        tool_call_chunks = {}  # Track partial tool calls by index
        
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
        return ''.join(content_chunks), tool_calls
    
    async def _test_connection(self) -> bool:
        """Test connection to the API endpoint"""
        try:
            stream = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": "test"}],
                max_completion_tokens=2,
                stream=True,
            )
            # Just collect the chunks to verify streaming works
            # We only need the content, ignore tool calls for connection testing
            _, _ = await self._collect_streaming_chunks_with_tools(stream)
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
