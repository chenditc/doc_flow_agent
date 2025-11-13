#!/usr/bin/env python3
"""Tracing-enabled tool wrappers
Provides tracing capabilities for tools while maintaining backward compatibility

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

from typing import Dict, Any, Optional
from tools.base_tool import BaseTool
from tracing import ExecutionTracer


class TracingToolWrapper:
    """Wrapper to add tracing capabilities to existing tools"""
    
    def __init__(self, tool: BaseTool, tracer: ExecutionTracer):
        self.tool = tool
        self.tracer = tracer
        # Delegate all attributes to the wrapped tool
        self.tool_id = tool.tool_id

    def __getattr__(self, name: str):  # pragma: no cover - simple delegation
        """Delegate attribute access to the wrapped tool when not found here.

        This allows transparent usage of the wrapper anywhere the original
        tool instance was expected. Only called if normal attribute lookup
        fails, so it won't interfere with our own attributes/methods.
        """
        return getattr(self.tool, name)



    async def execute(self, parameters: Dict[str, Any], sop_doc_body: Optional[str] = None) -> Any:
        """Execute tool with tracing"""
        try:
            # Log tool execution start
            result = await self.tool.execute(parameters, sop_doc_body=sop_doc_body)
            
            # Log successful tool execution
            self.tracer.log_tool_call(
                tool_id=self.tool_id,
                parameters=parameters,
                output=result
            )
            
            return result
        except Exception as e:
            # Log failed tool execution
            self.tracer.log_tool_call(
                tool_id=self.tool_id,
                parameters=parameters,
                output=None,
                error=e
            )
            raise

    def get_result_validation_hint(self) -> str:
        """Get result validation hint from the wrapped tool if available"""
        return self.tool.get_result_validation_hint()


class TracingLLMTool(TracingToolWrapper):
    """LLM tool with enhanced tracing for prompt/response logging"""

    def __init__(self, tool: BaseTool, tracer: ExecutionTracer):
        super().__init__(tool, tracer)
        register = getattr(self.tool, "register_call_logger", None)
        if callable(register):
            register(self._handle_llm_call_event)

    def _handle_llm_call_event(self, payload: Dict[str, Any]) -> None:
        """Receive raw LLM call metadata from the tool and forward to the tracer."""
        if not payload:
            return
        try:
            self.tracer.log_llm_call(
                prompt=payload.get('prompt', ''),
                response=payload.get('response', ''),
                model=payload.get('model'),
                tool_calls=payload.get('tool_calls'),
                token_usage=payload.get('token_usage'),
                all_parameters=payload.get('all_parameters'),
                start_time=payload.get('start_time'),
                end_time=payload.get('end_time')
            )
        except Exception as exc:  # pragma: no cover - logging should not break tool execution
            print(f"[TRACING LLM] Warning: failed to log LLM call: {exc}")

    async def execute(self, parameters: Dict[str, Any], sop_doc_body: Optional[str] = None, **kwargs) -> Any:
        """Execute LLM tool with enhanced tracing"""
        try:
            result = await self.tool.execute(parameters, sop_doc_body=sop_doc_body, **kwargs)

            # Also log as tool call
            self.tracer.log_tool_call(
                tool_id=self.tool_id,
                parameters=parameters,
                output=result
            )

            return result
        except Exception as e:
            self.tracer.log_tool_call(
                tool_id=self.tool_id,
                parameters=parameters,
                output=None,
                error=e
            )
            raise
