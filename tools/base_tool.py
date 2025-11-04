#!/usr/bin/env python3
"""Base Tool Class for Doc Flow Agent

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

import abc
from typing import Dict, Any, Optional


class BaseTool(abc.ABC):
    """Base class for all tools in the Doc Flow Agent"""
    
    def __init__(self, tool_id: str):
        """Initialize the tool with its ID
        
        Args:
            tool_id: Unique identifier for this tool
        """
        self.tool_id = tool_id
    
    @abc.abstractmethod
    async def execute(self, parameters: Dict[str, Any], sop_doc_body: Optional[str] = None, **kwargs) -> str:
        """Execute the tool with given parameters
        
        Args:
            parameters: Dictionary of parameters for the tool
            sop_doc_body: Optional raw SOP document body (markdown) associated with the task
            **kwargs: Extra optional arguments passed by the engine (e.g., doc_path)
            
        Returns:
            Tool output as string (usually JSON)
            
        Raises:
            ValueError: If required parameters are missing
            RuntimeError: If tool execution fails
        """
        pass
    
    def validate_parameters(self, parameters: Dict[str, Any], required_params: list) -> None:
        """Validate that all required parameters are present
        
        Args:
            parameters: Dictionary of parameters to validate
            required_params: List of required parameter names
            
        Raises:
            ValueError: If any required parameter is missing
        """
        missing_params = [param for param in required_params if param not in parameters]
        if missing_params:
            raise ValueError(f"{self.tool_id} tool requires parameters: {', '.join(missing_params)}")
    
    def __str__(self) -> str:
        return f"{self.__class__.__name__}(tool_id={self.tool_id})"
    
    def __repr__(self) -> str:
        return self.__str__()

    def get_result_validation_hint(self) -> str:
        """Return a hint string to help LLM validate the result of the tool call."""
        raise NotImplementedError("Subclasses must implement get_result_validation_hint()")