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
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o-2024-11-20")   
    
    async def execute(self, parameters: Dict[str, Any]) -> str:
        """Execute LLM tool with given parameters
        
        Args:
            parameters: Dictionary containing 'prompt' and optional parameters
            
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
        
        # Log the prompt being sent
        
        print(f"[LLM CALL] Prompt: {prompt[:100]}...")
        
        # Make actual OpenAI API call
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.7,
            max_tokens=4000
        )
        
        # Extract response content
        content = response.choices[0].message.content

        print(f"[LLM RESPONSE] {content}...")
        
        return content
    
    def _validate_api_key(self) -> bool:
        """Validate that API key is configured"""
        return bool(self.client.api_key)
    
    async def _test_connection(self) -> bool:
        """Test connection to the API endpoint"""
        try:
            await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": "test"}],
                max_tokens=1
            )
            return True
        except Exception as e:
            print(f"[LLM CONNECTION ERROR] {str(e)}")
            return False
