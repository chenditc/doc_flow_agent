#!/usr/bin/env python3
"""Template Tool for Doc Flow Agent

Template tool that uses f-string formatting to replace content in document templates.

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
from .base_tool import BaseTool


class TemplateTool(BaseTool):
    """Template tool for f-string style content replacement"""

    def __init__(self):
        super().__init__("TEMPLATE")

    async def execute(self, parameters: Dict[str, Any], sop_doc_body: Optional[str] = None) -> Dict[str, Any]:
        """Execute template tool with given parameters.
        
        This tool uses f-string style formatting to replace placeholders in the 
        document body template with values from parameters.
        
        Args:
            parameters: Dictionary containing template variables and a special
                       'template_content' key with the template body
                       
        Returns:
            Dictionary with 'content' key containing the formatted template
            
        Raises:
            ValueError: If template_content parameter is missing
            RuntimeError: If template formatting fails
        """
        # Determine template content: prefer provided sop_doc_body over parameters['template_content']
        template_content = sop_doc_body 
        if template_content is None:
            raise ValueError("sop_doc_body is required")
        
        print(f"[TEMPLATE CALL] Template length: {len(template_content)} characters")
        print(f"[TEMPLATE CALL] Parameters: {list(parameters.keys())}")

        # Create a copy of parameters without template_content for formatting
        format_params = {k: v for k, v in parameters.items() if k != 'template_content'}
        try:
            formatted_content = template_content.format(**format_params)

            # Detect actually used variables (simple placeholder scan)
            import re
            used_var_names = {m.group(1) for m in re.finditer(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}", template_content)}
            used_vars = {k: v for k, v in format_params.items() if k in used_var_names}

            print(f"[TEMPLATE RESULT] Formatted content length: {len(formatted_content)} characters")

            return {
                "content": formatted_content,
                "template_variables_used": used_vars if used_vars else {}
            }
        except KeyError as e:
            missing_key = str(e).strip("'\"")
            raise RuntimeError(f"Template formatting failed: missing variable '{missing_key}' in parameters")
        except Exception as e:
            raise RuntimeError(f"Template formatting failed: {str(e)}")

    def get_result_validation_hint(self) -> str:
        return (
            "The result is a template filled text, check if there is any unfilled variable like {variable} "
        )
