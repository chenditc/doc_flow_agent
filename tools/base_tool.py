#!/usr/bin/env python3
"""
Base Tool Class for Doc Flow Agent
"""

import abc
from typing import Dict, Any


class BaseTool(abc.ABC):
    """Base class for all tools in the Doc Flow Agent"""
    
    def __init__(self, tool_id: str):
        """Initialize the tool with its ID
        
        Args:
            tool_id: Unique identifier for this tool
        """
        self.tool_id = tool_id
    
    @abc.abstractmethod
    async def execute(self, parameters: Dict[str, Any]) -> str:
        """Execute the tool with given parameters
        
        Args:
            parameters: Dictionary of parameters for the tool
            
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
