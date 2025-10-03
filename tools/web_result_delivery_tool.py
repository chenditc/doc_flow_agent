#!/usr/bin/env python3
"""Web Result Delivery Tool for Doc Flow Agent
Tool for web-based result delivery to users (text, files, images)

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
import shutil
from pathlib import Path
from typing import Dict, Any, Optional, List

from .base_tool import BaseTool
from .llm_tool import LLMTool


class WebResultDeliveryTool(BaseTool):
    """Web-based result delivery tool for presenting results to users"""
    
    def __init__(self, llm_tool):
        super().__init__("WEB_RESULT_DELIVERY")
        self.llm_tool = llm_tool
    
    async def execute(self, parameters: Dict[str, Any], sop_doc_body: Optional[str] = None) -> Dict[str, Any]:
        """Execute web result delivery tool with given parameters
        
        Args:
            parameters: Dictionary containing:
                - result_data (str or dict): The result to display (text, JSON, etc.)
                  Can include file paths and image paths that need to be served
                - session_id (str): Session identifier
                - task_id (str): Task identifier
            
        Returns:
            Dictionary with result URL and status
            
        Raises:
            ValueError: If required parameters are missing
        """
        self.validate_parameters(parameters, ['result_data', 'session_id', 'task_id'])
        
        result_data = parameters.get('result_data', '')
        session_id = parameters.get('session_id', '')
        task_id = parameters.get('task_id', '')
        
        # Get base directory and create session/task directory
        # Reuse user_comm directory structure to avoid docker volume changes
        project_root = Path(__file__).parent.parent
        session_dir = project_root / "user_comm" / "sessions" / session_id / task_id
        index_file = session_dir / "index.html"
        files_dir = session_dir / "files"
        
        # Check if result already exists (idempotent)
        if index_file.exists():
            print(f"[WEB_RESULT_DELIVERY] Found existing result page for {session_id}/{task_id}")
            return {
                "result_url": self._get_result_url(session_id, task_id),
                "status": "ok",
                "existing": True
            }
        
        # Create directory structure
        session_dir.mkdir(parents=True, exist_ok=True)
        files_dir.mkdir(exist_ok=True)
        
        # Generate HTML page using LLM and get file mappings
        html_content, file_mappings = await self._generate_result_html_with_llm(
            result_data, session_id, task_id
        )
        
        # Copy files based on LLM-identified mappings
        self._copy_files_from_mappings(file_mappings, files_dir)
        
        # Write index.html atomically
        temp_index = index_file.with_suffix('.tmp')
        with open(temp_index, 'w', encoding='utf-8') as f:
            f.write(html_content)
        temp_index.replace(index_file)
        
        # Get result URL and notify user
        result_url = self._get_result_url(session_id, task_id)
        self._notify_user(result_url, session_id, task_id)
        
        print(f"[WEB_RESULT_DELIVERY] Result delivered for {session_id}/{task_id}")
        return {
            "result_url": result_url,
            "status": "ok",
            "existing": False
        }
    
    def _copy_files_from_mappings(self, file_mappings: List[Dict[str, str]], dest_dir: Path) -> None:
        """Copy files based on source-target mappings from LLM
        
        Args:
            file_mappings: List of dicts with 'source' and 'target' keys
            dest_dir: Destination directory for files
        """
        for mapping in file_mappings:
            source_path = mapping.get('source', '')
            target_filename = mapping.get('target', '')
            
            if not source_path or not target_filename:
                print(f"[WEB_RESULT_DELIVERY] Warning: Invalid mapping: {mapping}")
                continue
            
            source = Path(source_path)
            if not source.exists():
                print(f"[WEB_RESULT_DELIVERY] Warning: File not found: {source_path}")
                continue
            
            if not source.is_file():
                print(f"[WEB_RESULT_DELIVERY] Warning: Not a file: {source_path}")
                continue
            
            # Copy file to destination with target filename
            dest_file = dest_dir / target_filename
            try:
                shutil.copy2(source, dest_file)
                print(f"[WEB_RESULT_DELIVERY] Copied file: {source_path} -> {target_filename}")
            except Exception as e:
                print(f"[WEB_RESULT_DELIVERY] Error copying {source_path}: {e}")
    
    def _get_result_url(self, session_id: str, task_id: str) -> str:
        """Construct the result URL for the user."""
        base_url = os.getenv('VISUALIZATION_SERVER_URL', 'http://localhost:8000')
        if not base_url.startswith(('http://', 'https://')):
            print(f"[WEB_RESULT_DELIVERY] Warning: VISUALIZATION_SERVER_URL should include protocol, got: {base_url}")
            base_url = f"http://{base_url}"
        
        return f"{base_url}/result-delivery/{session_id}/{task_id}/"
    
    def _notify_user(self, result_url: str, session_id: str, task_id: str) -> None:
        """Notify user about the result using the notification system."""
        import sys
        from pathlib import Path
        # Add project root to path
        project_root = Path(__file__).parent.parent
        if str(project_root) not in sys.path:
            sys.path.insert(0, str(project_root))
        from utils.user_notify import notify_user
        
        message = f"Task result available:\nSession: {session_id}\nTask: {task_id}\nView at: {result_url}"
        notify_user(message)

    async def _generate_result_html_with_llm(
        self, 
        result_data: Any, 
        session_id: str, 
        task_id: str
    ) -> tuple[str, List[Dict[str, str]]]:
        """Generate HTML page using LLM and identify files/images to serve
        
        Returns:
            Tuple of (html_content, file_mappings)
            where file_mappings is a list of {source: local_path, target: filename}
        """
        
        # Convert result_data to string if it's a dict
        if isinstance(result_data, dict):
            result_text = json.dumps(result_data, indent=2, ensure_ascii=False)
        else:
            result_text = str(result_data)
        
        # Prepare prompt for LLM to generate the HTML page and identify files
        llm_prompt = f"""You are a web page generator for a result delivery system. Generate a complete HTML page with Material Design styling that displays task results to the user.

Result Data:
```
{result_text}
```

Your tasks:
1. Identify any file paths or image paths in the result data that need to be served to the user
2. For each identified file/image, determine:
   - source: The local file path (as it appears in result_data)
   - target: The filename to use when serving (just the filename, not full path)
3. Generate a complete HTML page that displays the result data

Requirements for HTML generation:
1. Create a complete, valid HTML page with proper DOCTYPE, head, and body
2. Use Material Design styling (include Google Fonts Roboto and Material Icons from CDN)
3. Display the result data in a clear, readable format:
   - Use appropriate formatting for text, JSON, or structured data
   - Use syntax highlighting for code/JSON if applicable
   - Make long text content scrollable and have a copy button
4. For any files you identified, create download buttons/links:
   - Use the URL pattern: /result-delivery/{session_id}/{task_id}/files/{{target_filename}}
   - Style as Material Design buttons with download icons
5. For any images you identified, display them inline in the page:
   - Use the URL pattern: /result-delivery/{session_id}/{task_id}/files/{{target_filename}}
   - Make images responsive and have a download button below
6. Use modern CSS with good UX (responsive, accessible, clean layout)
7. Add a header with a success icon and title "Task Result"
8. Make the page visually appealing and easy to read

Return both the HTML content and the file mappings using the provided tool."""

        # Create tool schema for HTML generation
        tool_schema = self._create_html_generation_tool_schema()

        # Use LLM tool to generate the HTML with tool calls
        llm_params = {
            "prompt": llm_prompt,
            "temperature": 0.0,
            "tools": [tool_schema]
        }
        llm_result = await self.llm_tool.execute(llm_params)
        
        # Extract HTML and file mappings from tool call response
        html_content, file_mappings = self._extract_html_from_response(llm_result)
        
        return html_content, file_mappings
    
    def _create_html_generation_tool_schema(self) -> Dict[str, Any]:
        """Create tool schema for HTML result page generation with file mapping
        
        Returns:
            Tool schema dictionary for use with LLMTool
        """
        tool_schema = {
            "type": "function",
            "function": {
                "name": "generate_html_result_page",
                "description": "Generate complete HTML result page for task result delivery and identify files to serve",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "html_content": {
                            "type": "string",
                            "description": "Complete HTML page content with proper DOCTYPE, styling and result display"
                        },
                        "file_mappings": {
                            "type": "array",
                            "description": "List of files/images that need to be copied from local paths to the serving directory",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "source": {
                                        "type": "string",
                                        "description": "Local file path as it appears in result_data (absolute or relative path)"
                                    },
                                    "target": {
                                        "type": "string",
                                        "description": "Target filename to use when serving (just filename, not path). This should match the filename used in HTML links/images."
                                    },
                                    "type": {
                                        "type": "string",
                                        "enum": ["file", "image"],
                                        "description": "Type of the file (for reference)"
                                    }
                                },
                                "required": ["source", "target", "type"]
                            }
                        }
                    },
                    "required": ["html_content", "file_mappings"]
                }
            }
        }
        
        return tool_schema

    def _extract_html_from_response(self, response) -> tuple[str, List[Dict[str, str]]]:
        """Extract HTML content and file mappings from LLM response with tool calls
        
        Args:
            response: LLM response containing tool calls
            
        Returns:
            Tuple of (html_content, file_mappings)
        """
        # Handle both string response (legacy) and tool call response
        if isinstance(response, str):
            return response, []
            
        # Extract tool calls from response
        tool_calls = response.get("tool_calls", [])
        if not tool_calls:
            # Fallback to direct response if no tool calls
            return str(response), []
        
        # Get the first (and should be only) tool call
        tool_call = tool_calls[0]
        if tool_call.get("name") != "generate_html_result_page":
            raise ValueError(f"Unexpected tool call: {tool_call.get('name')}")
        
        # Extract arguments
        arguments = tool_call.get("arguments", {})
        html_content = arguments.get("html_content", "")
        file_mappings = arguments.get("file_mappings", [])
        
        if not html_content:
            raise ValueError("No HTML content generated by LLM")
        
        print(f"[WEB_RESULT_DELIVERY] LLM identified {len(file_mappings)} files to serve")
        for mapping in file_mappings:
            print(f"[WEB_RESULT_DELIVERY]   {mapping.get('type', 'file')}: {mapping.get('source')} -> {mapping.get('target')}")
            
        return html_content, file_mappings

    def get_result_validation_hint(self) -> str:
        return "This step doesn't need validation as it generates a web page for user viewing."
