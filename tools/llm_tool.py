#!/usr/bin/env python3
"""
LLM Tool for Doc Flow Agent
Real OpenAI API implementation
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
        self.client = AsyncOpenAI(
            base_url=os.getenv("OPENAI_API_BASE", "https://openrouter.ai/api/v1"),
            api_key=os.getenv("OPENAI_API_KEY", "")
        )
        self.model = os.getenv("OPENAI_MODEL", "openai/gpt-4o-2024-11-20")   
    
    async def execute(self, parameters: Dict[str, Any]) -> str:
        """Execute LLM tool with given parameters
        
        Args:
            parameters: Dictionary containing 'prompt', optional 'tools' schema, and other parameters
            
        Returns:
            JSON string with LLM response
            
        Raises:
            ValueError: If prompt parameter is missing
        """
        self.validate_parameters(parameters, ['prompt'])
        if not self._validate_api_key():
            raise ValueError("API key is not configured or invalid")
        if not await self._test_connection():
            raise RuntimeError("Failed to connect to LLM API")
        
        prompt = parameters.get('prompt', '')
        tools = parameters.get('tools', None)
        
        # Log the prompt being sent
        print(f"[LLM CALL] Prompt: {prompt}...")
        if tools:
            print(f"[LLM CALL] Tools provided: {[tool.get('function', {}).get('name', 'unknown') for tool in tools]}")
        
        # Prepare API call parameters
        api_params = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.7,
            "max_tokens": 4000,
            "stream": True,
        }
        
        # Add tools if provided
        if tools:
            api_params["tools"] = tools
            api_params["tool_choice"] = "auto"
        
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

    
    def _validate_api_key(self) -> bool:
        """Validate that API key is configured"""
        return bool(self.client.api_key)
    
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
                max_tokens=2,
                stream=True,
            )
            # Just collect the chunks to verify streaming works
            # We only need the content, ignore tool calls for connection testing
            _, _ = await self._collect_streaming_chunks_with_tools(stream)
            return True
        except Exception as e:
            print(f"[LLM CONNECTION ERROR] {str(e)}")
            return False

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
