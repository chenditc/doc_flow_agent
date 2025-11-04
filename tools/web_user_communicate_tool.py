#!/usr/bin/env python3
"""Web User Communicate Tool for Doc Flow Agent
Tool for web-based interactive communication with users

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
import os
import asyncio
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional

from .base_tool import BaseTool
from .llm_tool import LLMTool


class WebUserCommunicateTool(BaseTool):
    """Web-based user communication tool for interactive message exchange"""
    
    def __init__(self, llm_tool):
        super().__init__("WEB_USER_COMMUNICATE")
        self.llm_tool = llm_tool
    
    async def execute(self, parameters: Dict[str, Any], sop_doc_body: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """Execute web user communicate tool with given parameters
        
        Args:
            parameters: Dictionary containing:
                - instruction (str): What needs to be collected from user
                - session_id (str): Session identifier
                - task_id (str): Task identifier
                - timeout_seconds (int, optional): Max wait time (default 1800)
                - poll_interval (float, optional): Polling interval (default 2.0)
            
        Returns:
            Dictionary with user's response or timeout status
            
        Raises:
            ValueError: If required parameters are missing
        """
        self.validate_parameters(parameters, ['instruction', 'session_id', 'task_id'])
        
        instruction = parameters.get('instruction', '')
        session_id = parameters.get('session_id', '')
        task_id = parameters.get('task_id', '')
        timeout_seconds = parameters.get('timeout_seconds', 1800)
        poll_interval = parameters.get('poll_interval', 2.0)
        
        # Get base directory and create session/task directory
        project_root = Path(__file__).parent.parent
        session_dir = project_root / "user_comm" / "sessions" / session_id / task_id
        response_file = session_dir / "response.json"
        index_file = session_dir / "index.html"
        
        # Check if response already exists (idempotent)
        if response_file.exists():
            with open(response_file, 'r', encoding='utf-8') as f:
                existing_response = json.load(f)
            print(f"[WEB_USER_COMMUNICATE] Found existing response for {session_id}/{task_id}")
            return {
                "instruction": instruction,
                "form_url": self._get_form_url(session_id, task_id),
                "answer": existing_response.get('answer', ''),
                "status": "ok",
                "existing": True
            }
        
        # Create directory structure
        session_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate HTML form using LLM
        html_content = await self._generate_form_html_with_llm(instruction, session_id, task_id)
        
        # Write index.html atomically
        temp_index = index_file.with_suffix('.tmp')
        with open(temp_index, 'w', encoding='utf-8') as f:
            f.write(html_content)
        temp_index.replace(index_file)
        
        # Get form URL and notify user
        form_url = self._get_form_url(session_id, task_id)
        self._notify_user(instruction, form_url)
        
        # Start polling for response
        start_time = time.monotonic()
        
        while time.monotonic() - start_time < timeout_seconds:
            if response_file.exists():
                with open(response_file, 'r', encoding='utf-8') as f:
                    response_data = json.load(f)
                
                print(f"[WEB_USER_COMMUNICATE] Received response for {session_id}/{task_id}")
                return {
                    "instruction": instruction,
                    "form_url": form_url,
                    "answer": response_data.get('answer', ''),
                    "status": "ok",
                    "existing": False
                }
            
            await asyncio.sleep(poll_interval)
        
        # Timeout reached
        print(f"[WEB_USER_COMMUNICATE] Timeout waiting for response from {session_id}/{task_id}")
        return {
            "instruction": instruction,
            "form_url": form_url,
            "status": "timeout"
        }
    
    def _get_form_url(self, session_id: str, task_id: str) -> str:
        """Construct the form URL for the user."""
        base_url = os.getenv('VISUALIZATION_SERVER_URL', 'http://localhost:8000')
        if not base_url.startswith(('http://', 'https://')):
            print(f"[WEB_USER_COMMUNICATE] Warning: VISUALIZATION_SERVER_URL should include protocol, got: {base_url}")
            base_url = f"http://{base_url}"
        
        return f"{base_url}/user-comm/{session_id}/{task_id}/"
    
    def _notify_user(self, instruction: str, form_url: str) -> None:
        """Notify user about the form using the notification system."""
        import sys
        from pathlib import Path
        # Add project root to path
        project_root = Path(__file__).parent.parent
        if str(project_root) not in sys.path:
            sys.path.insert(0, str(project_root))
        from utils.user_notify import notify_user
        
        message = f"User input required:\n{instruction}\nPlease visit: {form_url}"
        notify_user(message)

    async def _generate_form_html_with_llm(self, instruction: str, session_id: str, task_id: str) -> str:
        """Generate HTML form using LLM to interpret the instruction and create appropriate form fields."""
        
        # Prepare prompt for LLM to generate the HTML form
        llm_prompt = f"""You are a web form generator for a user communication system. Generate a complete HTML page with Material Design styling that creates an appropriate form based on the user instruction.

User Instruction: "{instruction}"

Requirements:
1. Create a complete, valid HTML page with proper DOCTYPE, head, and body
2. Use Material Design styling (include Google Fonts Roboto and Material Icons from CDN)
3. Analyze the instruction to determine what type of form fields are needed:
   - If asking for a simple response/feedback: use textarea
   - If asking to choose from options: use radio buttons or checkboxes
   - If asking for specific data: use appropriate input types (text, number, email, etc.)
   - If asking multiple questions: create multiple form sections
4. Include proper form validation and user-friendly labels
5. The form must submit to '/api/user-comm/submit' via POST with JSON containing session_id, task_id, and answer
   Example API call:
   ```javascript
   fetch('/api/user-comm/submit', {{
       method: 'POST',
       headers: {{ 'Content-Type': 'application/json' }},
       body: JSON.stringify({{
           session_id: '{session_id}',
           task_id: '{task_id}',
           answer: 'Which data center do you prefer? Answer: User response text here'
       }})
   }})
   ```
6. Include session info: Session: {session_id} | Task: {task_id}
7. Use modern CSS with good UX (responsive, accessible, loading states)
8. Include error handling and success messages
9. The answer field should contains both the question and user's response for clarity.
10. The form data should be collected into a single 'answer' field for submission (combine multiple fields if needed), use json stringify if needed.
11. IF the submit button return 200, alert user "Submission successful" and refresh the page after 3 seconds. If not 200, alert user "Submission failed, <xxx detailed error message from server>".

Generate ONLY the complete HTML content, no explanations or markdown formatting."""

        # Create tool schema for HTML generation
        tool_schema = self._create_html_generation_tool_schema()

        # Use LLM tool to generate the HTML with tool calls
        llm_params = {
            "prompt": llm_prompt,
            "temperature": 0.0,
            "tools": [tool_schema]
        }
        llm_result = await self.llm_tool.execute(llm_params)
        
        # Extract HTML from tool call response (no manual cleanup needed)
        html_content = self._extract_html_from_response(llm_result)
        
        return html_content
    
    def _create_html_generation_tool_schema(self) -> Dict[str, Any]:
        """Create tool schema for HTML form generation
        
        Returns:
            Tool schema dictionary for use with LLMTool
        """
        tool_schema = {
            "type": "function",
            "function": {
                "name": "generate_html_form",
                "description": "Generate complete HTML form page for user communication",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "html_content": {
                            "type": "string",
                            "description": "Complete HTML page content with proper DOCTYPE, styling and form functionality"
                        }
                    },
                    "required": ["html_content"]
                }
            }
        }
        
        return tool_schema

    def _extract_html_from_response(self, response) -> str:
        """Extract HTML content from LLM response with tool calls
        
        Args:
            response: LLM response containing tool calls
            
        Returns:
            Generated HTML content as string
        """
        # Handle both string response (legacy) and tool call response
        if isinstance(response, str):
            return response
            
        # Extract tool calls from response
        tool_calls = response.get("tool_calls", [])
        if not tool_calls:
            # Fallback to direct response if no tool calls
            return str(response)
        
        # Get the first (and should be only) tool call
        tool_call = tool_calls[0]
        if tool_call.get("name") != "generate_html_form":
            raise ValueError(f"Unexpected tool call: {tool_call.get('name')}")
        
        # Extract arguments
        arguments = tool_call.get("arguments", {})
        html_content = arguments.get("html_content", "")
        
        if not html_content:
            raise ValueError("No HTML content generated by LLM")
            
        return html_content

    def get_result_validation_hint(self) -> str:
        return "As long as we get some meaningful answer, consider this task as success."