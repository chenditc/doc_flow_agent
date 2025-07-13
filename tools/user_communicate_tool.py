#!/usr/bin/env python3
"""
User Communicate Tool for Doc Flow Agent
Tool for interactive communication with users
"""

import json
import sys
from typing import Dict, Any

from .base_tool import BaseTool


class UserCommunicateTool(BaseTool):
    """User communication tool for interactive message exchange"""
    
    def __init__(self):
        super().__init__("USER_COMMUNICATE")
    
    async def execute(self, parameters: Dict[str, Any]) -> str:
        """Execute user communicate tool with given parameters
        
        Args:
            parameters: Dictionary containing 'message' parameter
            
        Returns:
            JSON string with user's reply
            
        Raises:
            ValueError: If message parameter is missing
        """
        self.validate_parameters(parameters, ['message'])
        
        message = parameters.get('message', '')
        
        print(f"[USER_COMMUNICATE] Sending message to user:")
        print(f"{message}")
        print("\n" + "="*50)
        
        # Get user response - handle multiline input
        user_reply = self._get_multiline_input()
        
        return {
            "user_reply": user_reply
        }
    
    def _get_multiline_input(self) -> str:
        """Get multiline input from user
        
        Returns:
            User's complete response as string
        """
        print("Please enter your reply (press Ctrl+D on Unix/Ctrl+Z on Windows when finished, or type '###END###' on a new line):")
        
        lines = []
        try:
            while True:
                try:
                    line = input()
                    # Check for end marker
                    if line.strip() == "###END###":
                        break
                    lines.append(line)
                except EOFError:
                    # User pressed Ctrl+D (Unix) or Ctrl+Z (Windows)
                    break
        except KeyboardInterrupt:
            # User pressed Ctrl+C
            print("\nUser communication cancelled.")
            return ""
        
        # Join all lines with newlines
        user_reply = '\n'.join(lines).strip()
        
        if not user_reply:
            print("No input received from user.")
            return ""
        
        print(f"\n[USER_COMMUNICATE] Received reply ({len(user_reply)} characters)")
        return user_reply
