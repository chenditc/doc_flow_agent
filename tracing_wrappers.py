#!/usr/bin/env python3
"""
Tracing-enabled tool wrappers
Provides tracing capabilities for tools while maintaining backward compatibility
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
    
    async def execute(self, parameters: Dict[str, Any]) -> Any:
        """Execute tool with tracing"""
        try:
            # Log tool execution start
            result = await self.tool.execute(parameters)
            
            # Log successful tool execution
            if self.tracer.enabled:
                self.tracer.log_tool_call(
                    tool_id=self.tool_id,
                    parameters=parameters,
                    output=result
                )
            
            return result
        except Exception as e:
            # Log failed tool execution
            if self.tracer.enabled:
                self.tracer.log_tool_call(
                    tool_id=self.tool_id,
                    parameters=parameters,
                    output=None,
                    error=e
                )
            raise


class TracingLLMTool(TracingToolWrapper):
    """LLM tool with enhanced tracing for prompt/response logging"""
    
    async def execute(self, parameters: Dict[str, Any]) -> Any:
        """Execute LLM tool with enhanced tracing"""
        try:
            result = await self.tool.execute(parameters)
            
            # Log LLM call with prompt/response details
            if self.tracer.enabled:
                prompt = parameters.get('prompt', '')
                step = parameters.get('step')  # Optional step identifier
                model = getattr(self.tool, 'model', None)
                
                self.tracer.log_llm_call(
                    prompt=prompt,
                    response=result,
                    step=step,
                    model=model
                )
                
                # Also log as tool call
                self.tracer.log_tool_call(
                    tool_id=self.tool_id,
                    parameters=parameters,
                    output=result
                )
            
            return result
        except Exception as e:
            if self.tracer.enabled:
                self.tracer.log_tool_call(
                    tool_id=self.tool_id,
                    parameters=parameters,
                    output=None,
                    error=e
                )
            raise
