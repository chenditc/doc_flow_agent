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
import os
import yaml
import re
from pathlib import Path
from typing import Dict, List, Any, Optional, TYPE_CHECKING
from dataclasses import dataclass
from xml.sax.saxutils import escape

if TYPE_CHECKING:
    from sop_doc_vector_store import SOPDocVectorStore


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
    skip_new_task_generation: bool = False  # If true, engine should skip generating follow-up tasks
    requires_planning_metadata: bool = False  # If true, planner metadata should be injected for this SOP


class SOPDocumentLoader:
    """Handler for loading and parsing SOP documents"""
    
    def __init__(self, docs_dir: str = "sop_docs"):
        self.docs_dir = Path(docs_dir)
    
    def list_doc_ids(self) -> List[str]:
        """Return all SOP document IDs (relative paths without extension)."""
        if not self.docs_dir.exists():
            return []
        
        doc_ids: List[str] = []
        for path in self.docs_dir.rglob("*.md"):
            if path.is_file():
                relative = path.relative_to(self.docs_dir)
                doc_id = relative.with_suffix("").as_posix()
                doc_ids.append(doc_id)
        return sorted(doc_ids)
    
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
            print(f"Replace parameter in doc: {doc_path}")
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
            result_validation_rule=doc_data.get('result_validation_rule', ''),  # New field for result validation rule
            skip_new_task_generation=str(doc_data.get('skip_new_task_generation', 'false')).lower() == 'true',
            requires_planning_metadata=str(doc_data.get('requires_planning_metadata', 'false')).lower() == 'true'
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
        self._vector_store: Optional['SOPDocVectorStore'] = None
        # Default to a local on-disk cache directory so embeddings are reused across runs.
        # Can be overridden with EMBEDDING_CACHE_DIR.
        default_cache_dir = str((Path(__file__).resolve().parent / ".cache" / "embeddings").resolve())
        self.embedding_cache_dir = os.getenv("EMBEDDING_CACHE_DIR", default_cache_dir)
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
        description_lower = description.lower()

        for doc_id in all_doc_ids:
            # Skip doc IDs that contain only alphanumeric characters (too generic)
            if re.match(r'^[a-zA-Z0-9]+$', doc_id):
                continue
            
            # Use boundary matching that works for mixed-language text (ASCII and CJK)
            pattern = self._build_identifier_pattern(doc_id.lower())
            if re.search(pattern, description_lower):
                candidates.append((doc_id, "full_path"))
                print(f"[SOP_PARSER] Found candidate by full path match: {doc_id}")
        
        # 2. Try match file name without extension with word boundaries.
        for doc_id in all_doc_ids:
            filename = Path(doc_id).name
            # Skip filenames that contain only alphanumeric characters (too generic)
            if re.match(r'^[a-zA-Z0-9]+$', filename):
                continue

            # Use boundary matching that works for mixed-language text (ASCII and CJK)
            pattern = self._build_identifier_pattern(filename.lower())
            if re.search(pattern, description_lower):
                candidates.append((doc_id, "filename"))
                print(f"[SOP_PARSER] Found candidate by filename match: {doc_id}")

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
        return self.loader.list_doc_ids()

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
                
                
                available_tools.append({
                    "doc_id": doc_id,
                    "description": sop_doc.description,
                    "input_description": sop_doc.input_description,
                    "output_description": sop_doc.output_description,
                })
            except Exception as e:
                print(f"[TOOL_DISCOVERY] Warning: Could not load tool SOP {doc_id}: {e}")
                continue

        return available_tools
    
    def _build_valid_doc_id_list(
        self,
        available_tools: List[Dict[str, str]],
        vector_candidates: List[Dict[str, str]]
    ) -> List[str]:
        """Return ordered doc_id options for tool selection."""
        valid_docs: List[str] = [tool["doc_id"] for tool in available_tools if tool.get("doc_id")]
        if "general/plan" not in valid_docs:
            valid_docs.append("general/plan")

        for candidate in vector_candidates:
            doc_id = candidate.get("doc_id")
            if doc_id and doc_id not in valid_docs:
                valid_docs.insert(0, doc_id)
        return valid_docs

    def _format_doc_list_markdown(self, title: str, docs: List[Dict[str, str]]) -> str:
        """Return a simple markdown block summarizing doc IDs and descriptions."""
        lines = [f"{title}:"]
        if not docs:
            lines.append("<tool>")
            lines.append("  <tool_id>NONE</tool_id>")
            lines.append("  <tool_description>No tools available</tool_description>")
            lines.append("</tool>")
        else:
            for doc in docs:
                doc_id = escape(doc.get("doc_id", "unknown"))
                description = escape((doc.get("description") or "").strip())
                lines.append("<tool>")
                lines.append(f"  <tool_id>{doc_id}</tool_id>")
                lines.append(f"  <tool_description>{description}</tool_description>")
                lines.append("</tool>")
        return "\n".join(lines)

    def _sanitize_xml_tag_segment(self, value: str) -> str:
        sanitized = re.sub(r"[^a-zA-Z0-9_-]", "_", value.strip())
        return sanitized or "field"

    def _format_tool_prompt_entry(self, tool: Dict[str, Any]) -> str:
        doc_id = escape(tool.get("doc_id", ""))
        description = escape((tool.get("description") or "").strip())
        lines = [
            "  <tool>",
            f"    <doc_id>{doc_id}</doc_id>",
        ]
        if description:
            lines.append(f"    <description>{description}</description>")

        inputs = tool.get("input_description") or {}
        for key, desc in inputs.items():
            tag_name = f"input:{self._sanitize_xml_tag_segment(str(key))}"
            lines.append(f"    <{tag_name}>{escape(str(desc))}</{tag_name}>")
        output_desc = tool.get("output_description")
        if output_desc:
            tag_name = f"output:{self._sanitize_xml_tag_segment('description')}"
            lines.append(f"    <{tag_name}>{escape(str(output_desc))}</{tag_name}>")

        lines.append("  </tool>")
        return "\n".join(lines)
    
    async def get_planning_metadata(
        self,
        description: Optional[str] = None,
        *,
        include_vector_candidates: bool = True,
        vector_k: int = 5
    ) -> Dict[str, Any]:
        """Return metadata about available tool SOPs and similar documents.

        This helper consolidates the different discovery mechanisms we already
        have (explicit tool docs + vector search suggestions) so other prompts
        like planners or evaluators can inject the same information without
        reimplementing the logic.
        """
        available_tools = self._get_available_tools()
        vector_candidates: List[Dict[str, str]] = []
        if include_vector_candidates and description:
            vector_candidates = await self._get_vector_search_candidates(description, k=vector_k)
            vector_candidates = [vc for vc in vector_candidates if vc["doc_id"] not in {tool["doc_id"] for tool in available_tools}]

        valid_doc_ids = self._build_valid_doc_id_list(available_tools, vector_candidates)
        available_tools_markdown = self._format_doc_list_markdown(
            "Available tools (SOP references)",
            available_tools or []
        )
        vector_candidates_markdown = self._format_doc_list_markdown(
            "Vector-recommended tools",
            vector_candidates or []
        )

        return {
            "available_tools": available_tools,
            "vector_candidates": vector_candidates,
            "valid_doc_ids": valid_doc_ids,
            "available_tools_markdown": available_tools_markdown,
            "vector_candidates_markdown": vector_candidates_markdown,
            "available_tools_json": json.dumps(available_tools, ensure_ascii=False, indent=2),
            "vector_candidates_json": json.dumps(vector_candidates, ensure_ascii=False, indent=2)
        }
    
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
        
        # Include vector-search candidates to replicate real discovery flow.
        # Embeddings are cached on disk via EMBEDDING_CACHE_DIR / SOPDocVectorStore defaults.
        metadata = await self.get_planning_metadata(description, include_vector_candidates=True)
        available_tools = metadata["available_tools"]
        vector_candidates = metadata["vector_candidates"]
        valid_docs = metadata["valid_doc_ids"]

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

<available_tools>
"""
        for tool in available_tools:
            prompt += self._format_tool_prompt_entry(tool) + "\n"
        for candidate in vector_candidates:
            prompt += self._format_tool_prompt_entry(candidate) + "\n"
        prompt += "</available_tools>\n"
        
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
- If the task can be completed in one step using a single tool, set can_complete_with_tool to true and select the appropriate tool
- If the task If the task can be completed but it is complex and needs to be broken down into multiple steps, set can_complete_with_tool to false and select 'general/plan' 
- Consider the complexity, scope, and whether all necessary information is available.
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

    async def _get_vector_search_candidates(self, description: str, k: int = 5) -> List[Dict[str, str]]:
        """Return top-k SOP doc suggestions using the vector store."""
        store = await self._ensure_vector_store()
        if store is None:
            return []
        try:
            results = await store.similarity_search(description, k=k)
        except Exception as exc:  # pragma: no cover - defensive log
            print(f"[SOP_VECTOR_SEARCH] Failed to search vector store: {exc}")
            raise exc

        suggestions: List[Dict[str, str]] = []
        seen: set[str] = set()
        for result in results:
            doc_id = getattr(result, "doc_id", "")
            if not doc_id or doc_id in seen:
                continue
            suggestions.append({
                "doc_id": doc_id,
                "description": result.description,
            })
            seen.add(doc_id)
        return suggestions

    async def _ensure_vector_store(self) -> Optional['SOPDocVectorStore']:
        """Lazily build the SOP vector store the first time it's needed."""
        if self._vector_store is not None:
            return self._vector_store

        try:
            from sop_doc_vector_store import SOPDocVectorStore

            store = SOPDocVectorStore(
                docs_dir=str(self.loader.docs_dir),
                embedding_cache_dir=self.embedding_cache_dir or ""
            )
            await store.build()
            self._vector_store = store
        except Exception as exc:  # pragma: no cover - defensive log
            print(f"[SOP_VECTOR_SEARCH] Unable to initialize vector store: {exc}")
            raise exc
        return self._vector_store
    
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
            "prompt": prompt,
            "model": llm_tool.small_model  # Use smaller model for efficiency
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

    @staticmethod
    def _build_identifier_pattern(identifier: str) -> str:
        """Build a regex pattern that treats CJK characters as valid boundaries alongside word boundaries."""
        escaped_identifier = re.escape(identifier)
        # Allow matches when surrounded by standard word boundaries or directly adjacent to CJK characters.
        leading_boundary = r'(?:(?<=\b)|(?<=[\u4e00-\u9fff]))'
        trailing_boundary = r'(?:(?=\b)|(?=[\u4e00-\u9fff]))'
        return f"{leading_boundary}{escaped_identifier}{trailing_boundary}"
            

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
