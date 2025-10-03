#!/usr/bin/env python3
"""SOP Document handling and parsing functionality

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
import yaml
import re
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass


@dataclass
class SOPDocument:
    """Parsed SOP document"""
    doc_id: str
    description: str
    aliases: List[str]
    tool: Dict[str, Any]
    input_json_path: Dict[str, str]
    output_json_path: str  # Changed from Dict[str, Any] to str - now holds jsonpath
    body: str
    parameters: Dict[str, str]  # New field for markdown sections
    input_description: Dict[str, str]  # New field for input descriptions
    output_description: str  # New field for output description
    result_validation_rule: str  # New field for result validation rule


class SOPDocumentLoader:
    """Handler for loading and parsing SOP documents"""
    
    def __init__(self, docs_dir: str = "sop_docs"):
        self.docs_dir = Path(docs_dir)
    
    def load_sop_document(self, doc_id: str) -> SOPDocument:
        """Load and parse a SOP document by doc_id"""
        doc_path = self.docs_dir / f"{doc_id}.md"
        
        if not doc_path.exists():
            raise FileNotFoundError(f"SOP document not found: {doc_path}")
        
        with open(doc_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Split YAML front matter and body
        if content.startswith('---\n'):
            parts = content.split('---', 2)
            if len(parts) >= 3:
                yaml_content = parts[1]
                body = parts[2]
            else:
                raise ValueError(f"Invalid document format: {doc_path}, not enough parts --- splitter.")
        else:
            raise ValueError(f"Document missing YAML front matter: {doc_path}")
        
        # Parse YAML
        doc_data = yaml.safe_load(yaml_content)
        
        # Validate required fields
        if 'tool' not in doc_data:
            raise ValueError(f"SOP document missing required 'tool' field: {doc_path}")
        
        if 'tool_id' not in doc_data.get('tool', {}):
            raise ValueError(f"SOP document missing required 'tool.tool_id' field: {doc_path}")
        
        # Parse markdown sections from body
        parameters = self._parse_markdown_sections(body)
        
        # Replace tool parameters with matching markdown sections
        tool_data = doc_data.get('tool', {})
        if 'parameters' in tool_data:
            tool_data = self._replace_tool_parameters_with_sections(tool_data, parameters)
        
        return SOPDocument(
            doc_id=doc_data.get('doc_id', doc_id),
            description=doc_data.get('description', ''),
            aliases=doc_data.get('aliases', []),
            tool=tool_data,
            input_json_path=doc_data.get('input_json_path', {}),
            output_json_path=doc_data.get('output_json_path', ''),
            body=body,
            parameters=parameters,
            input_description=doc_data.get('input_description', {}),  # New field for input descriptions
            output_description=doc_data.get('output_description', ''),  # New field for output description
            result_validation_rule=doc_data.get('result_validation_rule', '')  # New field for result validation rule
        )
    
    def _parse_markdown_sections(self, body: str) -> Dict[str, str]:
        """Parse markdown sections and return them as key-value pairs using title as key"""
        parameters = {}
        
        # Find all markdown sections with ## headers
        section_pattern = r'^## (.+?)\n(.*?)(?=^## |\Z)'
        matches = re.findall(section_pattern, body, re.MULTILINE | re.DOTALL)
        
        for title, content in matches:
            # Clean up the title (remove any extra whitespace)
            clean_title = title.strip()
            # Clean up the content (remove leading/trailing whitespace but preserve internal formatting)
            clean_content = content.strip()
            parameters[clean_title] = clean_content
        
        return parameters
    
    def _replace_tool_parameters_with_sections(self, tool_data: Dict[str, Any], parameters: Dict[str, str]) -> Dict[str, Any]:
        """Replace tool parameters with matching markdown sections"""
        if 'parameters' not in tool_data:
            return tool_data
        
        # Create a copy to avoid modifying the original
        updated_tool = tool_data.copy()
        updated_parameters = updated_tool['parameters'].copy()
        
        # Check each parameter in tool.parameters
        for param_key, param_value in updated_parameters.items():
            # If the parameter value references a section (e.g., "{parameters.prompt}")
            if isinstance(param_value, str) and param_value.startswith('{parameters.') and param_value.endswith('}'):
                # Extract the section name (e.g., "parameters.prompt" -> "parameters.prompt")
                section_ref = param_value[1:-1]  # Remove the curly braces
                
                # Check if we have a matching section in parameters
                if section_ref in parameters:
                    updated_parameters[param_key] = parameters[section_ref]
                    print(f"[SOP_LOADER] Replaced {param_key} with section '{section_ref}'")
        
        updated_tool['parameters'] = updated_parameters
        return updated_tool


class SOPDocumentParser:
    """Parser for extracting context and doc_id from natural language descriptions"""
    
    def __init__(self, docs_dir: str = "sop_docs", llm_tool=None, tracer=None):
        self.loader = SOPDocumentLoader(docs_dir)
        self.llm_tool = llm_tool
        self.tracer = tracer
        if self.tracer is None:
            # For backwards compatibility in tests, create a minimal tracer
            from tracing import ExecutionTracer
            self.tracer = ExecutionTracer(enabled=False)
    
    async def parse_sop_doc_id_from_description(self, description: str, completed_tasks_info: List[Dict[str, str]] = None) -> tuple[str, str]:
        """Parse sop_doc_id from natural language description using patterns
        
        This is a unified interface for natural language -> sop_doc_id mapping.
        Can be extended to more sophisticated parsing in the future.
        
        Args:
            description: The task description to parse
            completed_tasks_info: Optional list of completed task info dicts with 'short_name' and 'output_json_path' keys
        
        Returns:
            tuple[str, str]: (sop_doc_id, doc_selection_message)
        """
        
        # Get all possible SOP document IDs, currently all files in the docs directory
        all_doc_ids = self._get_all_doc_ids()
        
        # Try match each one in the description and get possible doc_id
        candidates = []
        
        # 1. Try match full path with word boundaries.
        for doc_id in all_doc_ids:
            # Skip doc IDs that contain only alphanumeric characters (too generic)
            if re.match(r'^[a-zA-Z0-9]+$', doc_id):
                continue
            
            # Use word boundary matching instead of substring matching
            pattern = r'\b' + re.escape(doc_id.lower()) + r'\b'
            if re.search(pattern, description.lower()):
                candidates.append((doc_id, "full_path"))
        
        # 2. Try match file name without extension with word boundaries.
        for doc_id in all_doc_ids:
            filename = Path(doc_id).name
            
            # Use word boundary matching instead of substring matching
            pattern = r'\b' + re.escape(filename.lower()) + r'\b'
            if re.search(pattern, description.lower()):
                candidates.append((doc_id, "filename"))

        # Log candidate documents to tracing system
        candidate_doc_ids = [candidate[0] for candidate in candidates]

        candidate_doc_ids = list(set(candidate_doc_ids))
        
        # Use document selection tracing context manager
        with self.tracer.trace_document_selection_step() as doc_ctx:
            if not candidates:
                print("No candidate documents found, trying tool selection")
                # No direct matches found, use LLM to determine if task can be completed by a tool
                selected_tool_doc, doc_selection_message = await self._select_tool_for_task(description, completed_tasks_info)
                
                doc_ctx.set_result(
                    candidate_docs=[],
                    selected_doc=selected_tool_doc
                )
                
                return selected_tool_doc, doc_selection_message

            # Validate matched doc_id against description using LLM
            # Optimization: If there's exactly one unique candidate and the user explicitly
            # references it with any configured pattern, we can skip LLM disambiguation.
            # Patterns list is maintained centrally so future additions are easy.
            if len(candidate_doc_ids) == 1:
                single_candidate = candidate_doc_ids[0]
                if self._matches_explicit_doc_reference(description, single_candidate):
                    doc_ctx.set_result(candidate_docs=candidate_doc_ids, selected_doc=single_candidate)
                    return single_candidate, ""

            # Fall back to LLM disambiguation when multiple candidates or no explicit pattern
            best_doc_id = await self._validate_with_llm(description, candidates, all_doc_ids)
            
            doc_ctx.set_result(
                candidate_docs=candidate_doc_ids,
                selected_doc=best_doc_id
            )
            
            # No message for direct matches
            return best_doc_id, ""
    
    def _get_all_doc_ids(self) -> List[str]:
        """Get all available SOP document IDs from the docs directory"""
        doc_ids = []
        
        def scan_directory(directory: Path, relative_path: str = ""):
            """Recursively scan directory for .md files"""
            if not directory.exists():
                return
            
            for item in directory.iterdir():
                if item.is_file() and item.suffix == '.md':
                    # Build relative path from docs directory
                    if relative_path:
                        doc_id = f"{relative_path}/{item.stem}"
                    else:
                        doc_id = item.stem
                    doc_ids.append(doc_id)
                elif item.is_dir():
                    # Recursively scan subdirectories
                    next_relative = f"{relative_path}/{item.name}" if relative_path else item.name
                    scan_directory(item, next_relative)
        
        scan_directory(self.loader.docs_dir)
        return doc_ids
    
    def _get_available_tools(self) -> List[Dict[str, str]]:
        """Get available tool SOPs by scanning the tools directory"""
        available_tools = []
        
        tools_dir = self.loader.docs_dir / "tools"
        if not tools_dir.exists():
            return available_tools
        
        for tool_file in tools_dir.glob("*.md"):
            doc_id = f"tools/{tool_file.stem}"
            try:
                # Load the SOP document to get description
                sop_doc = self.loader.load_sop_document(doc_id)
                
                # Map tool descriptions to use cases based on tool_id
                use_case_map = {
                    "CLI": "File operations, system commands, running scripts, installing packages",
                    "LLM": "Text analysis, content generation, writing, planning, reasoning tasks", 
                    "PYTHON_EXECUTOR": "Data processing, calculations, REST API calls, complex logic, file manipulation",
                    "WEB_USER_COMMUNICATE": "Getting user input, asking questions, manual tasks requiring human intervention, use it very carefully, only ask user question when you are sure you need the user's input."
                }
                
                tool_id = sop_doc.tool.get('tool_id', '')
                # Use predefined use case if available, otherwise use the tool's description from the document
                use_case = use_case_map.get(tool_id, sop_doc.description)
                
                available_tools.append({
                    "doc_id": doc_id,
                    "description": sop_doc.description,
                    "use_case": use_case
                })
            except Exception as e:
                print(f"[TOOL_DISCOVERY] Warning: Could not load tool SOP {doc_id}: {e}")
                continue
        
        return available_tools
    
    async def _select_tool_for_task(self, description: str, completed_tasks_info: List[Dict[str, str]] = None) -> tuple[str, str]:
        """Use LLM to determine if task can be completed by any available tool or needs planning
        
        Args:
            description: The task description to analyze
            completed_tasks_info: Optional list of completed task info dicts with 'short_name' and 'output_json_path' keys
        
        Returns:
            tuple[str, str]: (selected_doc_id, message_to_user)
        """
        
        from tools.llm_tool import LLMTool
        
        # Use injected LLM tool if available, otherwise create a new one
        llm_tool = self.llm_tool if self.llm_tool is not None else LLMTool()
        
        # Get available tool SOPs dynamically
        available_tools = self._get_available_tools()
        
        # Build valid doc IDs from available tools
        valid_docs = [tool["doc_id"] for tool in available_tools] + ["general/plan"]
        
        # Create tool schema for tool selection
        tool_selection_schema = {
            "type": "function",
            "function": {
                "name": "select_tool_for_task",
                "description": "Determine if task can be completed by a single tool or needs breakdown",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "reasoning": {
                            "type": "string",
                            "description": "Brief explanation of why this tool is appropriate or why the task needs breakdown"
                        },
                        "can_complete_with_tool": {
                            "type": "boolean",
                            "description": "True if task can be completed with a single tool, False if needs breakdown"
                        },
                        "selected_tool_doc": {
                            "type": "string",
                            "description": f"The doc_id of the selected tool or 'general/plan' if needs breakdown. Valid options: {', '.join(valid_docs)}",
                            "enum": valid_docs
                        },
                        "message_to_user": {
                            "type": "string",
                            "description": "If selected_tool_doc is 'tools/web_user_communicate', provide a clear message asking the user for the missing information needed to complete the task"
                        }
                    },
                    "required": ["can_complete_with_tool", "selected_tool_doc", "reasoning"]
                }
            }
        }
        
        # Create prompt for tool selection
        prompt = f"""Analyze this task description and determine if it can be completed without more information, then determine if it can be completed using one of the available tools, or if it needs to be broken down into multiple steps. Only use the tool if the tool is good at it, eg. LLM is good at non exact match, python is good at exact match. 

You can complete almost anything using python + llm tool. Any task can be completed by using code to automate and use llm to think.

Available tools:
"""
        
        for tool in available_tools:
            prompt += f"- {tool['doc_id']}: {tool['description']}\n  Use cases: {tool['use_case']}\n\n"
        
        # Add previous executed tasks information if available
        previous_tasks_section = ""
        if completed_tasks_info:
            previous_tasks_section = "\n<previous executed tasks and output json paths>\n"
            for task_info in completed_tasks_info:
                short_name = task_info.get('short_name', 'Unknown Task')
                output_path = task_info.get('output_json_path', 'No output path')
                previous_tasks_section += f"- Task: {short_name}\n  Output available at: {output_path}\n\n"
            previous_tasks_section += "</previous executed tasks and output json paths>\n"
        
        prompt += f"""
Guidelines:
- If the task already contain enough information to complete or we can provide good guess for missing information, then try to see if there is suitable tool to complete it in one go. Otherwise, the information can only be obtain from user, select 'tools/web_user_communicate' to ask for more information.
- If the task can be completed in one step using a single tool, set can_complete_with_tool to true and select the appropriate tool
- If the task If the task can be completed but it is complex and needs to be broken down into multiple steps, set can_complete_with_tool to false and select 'general/plan' 
- Consider the complexity, scope, and whether all necessary information is available.
- If you select 'tools/web_user_communicate', you MUST provide a message_to_user that clearly explains what information is missing and asks the user to provide it.
- Consider the information available from previously executed tasks when determining if enough information is available.
{previous_tasks_section}
<task to analyze>
{description}
</task to analyze>

Please use the select_tool_for_task function to provide your analysis.
"""
        
        # Get LLM response
        response = await llm_tool.execute({
            "prompt": prompt,
            "tools": [tool_selection_schema]
        })
        
        # Extract results from tool call
        tool_calls = response.get("tool_calls", [])
        if not tool_calls:
            print("[TOOL_SELECTION] No tool calls found, defaulting to general/plan")
            return "general/plan", ""
        
        tool_call = tool_calls[0]
        if tool_call.get("name") != "select_tool_for_task":
            raise ValueError(f"Unexpected tool call: {tool_call.get('name')}, expected 'select_tool_for_task'")
        
        arguments = tool_call.get("arguments", {})
        can_complete = arguments.get("can_complete_with_tool", False)
        selected_doc = arguments.get("selected_tool_doc", "general/plan")
        reasoning = arguments.get("reasoning", "No reasoning provided")
        message_to_user = arguments.get("message_to_user", "")
        
        print(f"[TOOL_SELECTION] Can complete with tool: {can_complete}")
        print(f"[TOOL_SELECTION] Selected doc: {selected_doc}")
        print(f"[TOOL_SELECTION] Reasoning: {reasoning}")
        if message_to_user:
            print(f"[TOOL_SELECTION] Message to user: {message_to_user}")
        
        # Validate the selected tool doc exists
        if selected_doc not in valid_docs:
            raise ValueError(f"Invalid tool selection: {selected_doc}, valid options are: {', '.join(valid_docs)}")
        
        return selected_doc, message_to_user
    
    async def _validate_with_llm(self, description: str, candidates: List[tuple], all_doc_ids: List[str]) -> str:
        """Use LLM to validate and select the best matching doc_id"""

        from tools.llm_tool import LLMTool
        from datetime import datetime
        
        # Use injected LLM tool if available, otherwise create a new one
        llm_tool = self.llm_tool if self.llm_tool is not None else LLMTool()
        
        # Prepare candidate information for LLM
        candidate_info = []
        for doc_id, match_type in candidates:
            doc = self.loader.load_sop_document(doc_id)
            candidate_info.append({
                "doc_id": doc_id,
                "description": doc.description,
                "aliases": doc.aliases,
                "match_type": match_type
            })
        
        # Create prompt for LLM validation
        prompt = f"""Given the user's request: 
        
<user request>
{description}
</user request>

Please select the most appropriate SOP document from the following candidates:

"""
        for i, candidate in enumerate(candidate_info, 1):
            prompt += f"{i}. doc_id: {candidate['doc_id']}\n"
            prompt += f"   description: {candidate['description']}\n"
            prompt += f"   aliases: {', '.join(candidate['aliases'])}\n"
            prompt += f"   match_type: {candidate['match_type']}\n\n"
        
        prompt += "Please respond the doc_id in xml format: <doc_id>....</doc_id> with ONLY the doc_id of the best match.\n"
        prompt += " If none of the candidates are appropriate, respond with <doc_id>NONE</doc_id>."
        
        # Track timing for LLM call
        start_time = datetime.now().isoformat()
        
        # Get LLM response
        response = await llm_tool.execute({
            "prompt": prompt
        })
        
        # Note: LLM call is automatically logged by the tracer context
        
        # Extract content from new response format
        response_content = response["content"]
        
        response = re.search(r'<doc_id>(.*?)</doc_id>', response_content)

        if response:
            response = response.group(1).strip()
        
        if response == "NONE":
            return None

        # Validate LLM response in original list
        if response in [c['doc_id'] for c in candidate_info]:
            return response
        
        # If LLM response is invalid, return None
        return None

    # ------------- Explicit reference helpers -------------
    def _explicit_doc_reference_patterns(self, doc_id: str):
        """Return a list of compiled regex patterns that count as explicit references to doc_id.

        Current patterns include:
        1. Follow {doc_id}
        2. !`{doc_id}`
        3. 根据 {doc_id}.md   (space optional)
        4. 根据 {file_name}.md (when only file name used)
        5. 根据文档{doc_id}
        6. 根据文档{file_name}

        Note: We match both full doc_id (which may include path segments) and the terminal file name.
        To extend: add new regexes referencing doc_id_escaped or file_name_escaped.
        """
        file_name = Path(doc_id).name
        doc_id_escaped = re.escape(doc_id)
        file_name_escaped = re.escape(file_name)
        patterns = []
        for key_word in [file_name, doc_id_escaped, file_name_escaped]:
            patterns += [
                re.compile(rf"Follow\s+{key_word}", re.IGNORECASE),
                re.compile(rf"!`{key_word}`"),
                # Chinese patterns (space optional before file name), allow both full doc_id and just file name
                re.compile(rf"根据\s*{key_word}"),
                re.compile(rf"根据文档\s*{key_word}"),
            ]
        return patterns

    def _matches_explicit_doc_reference(self, description: str, doc_id: str) -> bool:
        """Check if description contains an explicit reference to doc_id using known patterns."""
        for pattern in self._explicit_doc_reference_patterns(doc_id):
            if pattern.search(description):
                return True
        return False
            

if __name__ == "__main__":
    # Example usage
    loader = SOPDocumentLoader()
    try:
        doc = loader.load_sop_document("general/fallback")
        print(f"Loaded SOP Document: {doc.doc_id}")
        print(f"Description: {doc.description}")
        print(f"Aliases: {', '.join(doc.aliases)}")
        print(f"Tool Parameters: {json.dumps(doc.tool, ensure_ascii=False, indent=2)}")
    except Exception as e:
        print(f"Error loading SOP document: {e}")