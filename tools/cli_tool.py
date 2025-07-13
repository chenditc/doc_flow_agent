#!/usr/bin/env python3
"""
CLI Tool for Doc Flow Agent
Tool for executing command line interface commands
"""

import asyncio
import json
from typing import Dict, Any

from .base_tool import BaseTool


class CLITool(BaseTool):
    """Command Line Interface tool for executing shell commands"""
    
    def __init__(self):
        super().__init__("CLI")
    
    async def execute(self, parameters: Dict[str, Any]) -> str:
        """Execute CLI tool with given parameters
        
        Args:
            parameters: Dictionary containing 'command' parameter
            
        Returns:
            Command output as string
            
        Raises:
            ValueError: If command parameter is missing
            RuntimeError: If command execution fails
        """
        self.validate_parameters(parameters, ['command'])
        
        command = parameters.get('command', '')
        
        print(f"[CLI CALL] Command: {command}")
        
        # Execute command asynchronously
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            raise RuntimeError(f"CLI command failed: {stderr.decode()}")
        
        return {
            "stdout": stdout.decode(),
            "stderr": stderr.decode()
        }
    
    def validate_command_safety(self, command: str) -> bool:
        """Validate that command is safe to execute
        
        Args:
            command: Command string to validate
            
        Returns:
            True if command appears safe, False otherwise
        """
        # TODO: Implement command safety validation
        # - Check for dangerous commands (rm -rf, format, etc.)
        # - Validate against whitelist of allowed commands
        # - Check for command injection attempts
        dangerous_patterns = ['rm -rf', 'format', 'del /f', 'sudo rm']
        return not any(pattern in command.lower() for pattern in dangerous_patterns)
