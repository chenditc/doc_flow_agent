#!/usr/bin/env python3
"""
SOP Document handling and parsing functionality
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
            output_description=doc_data.get('output_description', '')  # New field for output description
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
    
    async def parse_sop_doc_id_from_description(self, description: str) -> str:
        """Parse sop_doc_id from natural language description using patterns
        
        This is a unified interface for natural language -> sop_doc_id mapping.
        Can be extended to more sophisticated parsing in the future.
        """
        
        # Get all possible SOP document IDs, currently all files in the docs directory
        all_doc_ids = self._get_all_doc_ids()
        
        # Try match each one in the description and get possible doc_id
        candidates = []
        
        # 1. Try match full path.
        for doc_id in all_doc_ids:
            if doc_id.lower() in description.lower():
                candidates.append((doc_id, "full_path"))
        
        # 2. Try match file name without extension.
        for doc_id in all_doc_ids:
            filename = Path(doc_id).name
            if filename.lower() in description.lower():
                candidates.append((doc_id, "filename"))

        # Log candidate documents to tracing system
        candidate_doc_ids = [candidate[0] for candidate in candidates]

        candidate_doc_ids = list(set(candidate_doc_ids))
        
        # Use document selection tracing context manager
        with self.tracer.trace_document_selection_step() as doc_ctx:
            if not candidates:
                print("No candidate documents found")
                return None

            # Validate matched doc_id against description using LLM
            best_doc_id = await self._validate_with_llm(description, candidates, all_doc_ids)
            
            doc_ctx.set_result(
                candidate_docs=candidate_doc_ids,
                selected_doc=best_doc_id
            )
            
            return best_doc_id
    
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
        prompt = f"""Given the user's request: "{description}"

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