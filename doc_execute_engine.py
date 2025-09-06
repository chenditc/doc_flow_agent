#!/usr/bin/env python3
"""
Doc Flow Agent - Document Execute Engine
Minimal async engine for executing SOP documents.
"""

import json
import asyncio
import uuid
import re
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
import subprocess
import json_repair

import yaml
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from sop_document import SOPDocument, SOPDocumentLoader, SOPDocumentParser
from tools import BaseTool, LLMTool, CLITool, UserCommunicateTool
from tools.python_executor_tool import PythonExecutorTool
from tools.json_path_generator import SmartJsonPathGenerator
import jsonpath_ng
from jsonpath_ng.ext import parse
from utils import set_json_path_value
from exceptions import TaskInputMissingError, TaskCreationError
from tracing import ExecutionTracer, ExecutionStatus
from tracing_wrappers import TracingToolWrapper, TracingLLMTool


@dataclass
class PendingTask:
    """A reference to a task with metadata for stack management"""
    description: str
    task_id: str = None
    short_name: str = None
    parent_task_id: Optional[str] = None
    generated_by_phase: Optional[str] = None
    
    def __post_init__(self):
        # Auto-generate task_id if not provided
        if self.task_id is None:
            self.task_id = str(uuid.uuid4())
        
        # Auto-generate short_name if not provided
        if self.short_name is None:
            self.short_name = self._generate_simple_short_name(self.description)
    
    def _generate_simple_short_name(self, description: str) -> str:
        """Generate a simple short name from task description"""
        # Simple implementation: first 50 characters + "..." if truncated
        if len(description) <= 50:
            return description
        else:
            return description[:47] + "..."


@dataclass
class Task:
    """A task to be executed"""
    task_id: str
    description: str
    sop_doc_id: str
    tool: Dict[str, Any]
    input_json_path: Dict[str, str]
    output_json_path: str  # Holds jsonpath for output location
    short_name: str = None  # Short name for visualization (auto-generated if None)
    parent_task_id: Optional[str] = None  # Parent task relationship  
    output_description: str = None  # Store output description for dynamic path generation
    
    def __post_init__(self):
        # Auto-generate short_name if not provided
        if self.short_name is None:
            self.short_name = self._generate_simple_short_name(self.description)
    
    def _generate_simple_short_name(self, description: str) -> str:
        """Generate a simple short name from task description"""
        # Simple implementation: first 50 characters + "..." if truncated
        if len(description) <= 50:
            return description
        else:
            return description[:47] + "..."

    def __str__(self):
        # Return all fields as a formatted string for easy logging
        return (f"Task ID: {self.task_id}\n"
                f"Description: {self.description}\n"
                f"Short Name: {self.short_name}\n"
                f"Parent Task ID: {self.parent_task_id}\n"
                f"SOP Document ID: {self.sop_doc_id}\n"
                f"Tool: {self.tool.get('tool_id', 'N/A')}\n"
                f"Input JSON Paths: {json.dumps(self.input_json_path, ensure_ascii=False)}\n"
                f"Output JSON Path: {self.output_json_path}\n"
                f"Output Description: {self.output_description}")
    
    def __repr__(self):
        # Return a concise representation for debugging
        return (f"Task(task_id={self.task_id}, description={self.description}, "
                f"short_name={self.short_name}, parent_task_id={self.parent_task_id}, "
                f"sop_doc_id={self.sop_doc_id}, tool={self.tool.get('tool_id', 'N/A')}, "
                f"input_json_path={self.input_json_path}, output_json_path={self.output_json_path}, "
                f"output_description={self.output_description})")

class DocExecuteEngine:
    """Main execution engine for document-driven tasks"""
    
    def __init__(self, docs_dir: str = "sop_docs", context_file: str = "context.json", 
                 enable_tracing: bool = True, trace_output_dir: str = "traces"):
        self.docs_dir = Path(docs_dir)
        self.context_file = Path(context_file)
        self.context = {}
        self.task_stack: List[PendingTask] = []
        self.pending_tasks: Dict[str, PendingTask] = {}  # Index by task_id for quick lookups
        self.task_execution_counter = 0  # Counter for executed tasks
        self.task_retry_count = {}  # Track retry attempts for failed tasks
        self.max_retries = 3  # Maximum retry attempts per task
        self.last_task_output = None  # Store the last task output
        # Centralized map to store task short names by task_id for cross-references
        self.task_short_name_map: Dict[str, str] = {}
        
        # Initialize tracing
        self.tracer = ExecutionTracer(output_dir=trace_output_dir, enabled=enable_tracing)
        
        # Wrap tools with tracing if enabled
        if enable_tracing:
            llm_tool = TracingLLMTool(LLMTool(), self.tracer)
            self.tools = {
                "LLM": llm_tool,
                "CLI": TracingToolWrapper(CLITool(), self.tracer),
                "USER_COMMUNICATE": TracingToolWrapper(UserCommunicateTool(), self.tracer),
                "PYTHON_EXECUTOR": TracingToolWrapper(PythonExecutorTool(llm_tool=llm_tool), self.tracer)
            }
        else:
            self.tools = {
                "LLM": LLMTool(),
                "CLI": CLITool(),
                "USER_COMMUNICATE": UserCommunicateTool(),
                "PYTHON_EXECUTOR": PythonExecutorTool(llm_tool=LLMTool())
            }
        
        # Initialize SOPDocument components
        self.sop_loader = SOPDocumentLoader(docs_dir)
        self.sop_parser = SOPDocumentParser(docs_dir, llm_tool=self.tools.get("LLM"), tracer=self.tracer)
        
        # Initialize JSON path generator
        self.json_path_generator = SmartJsonPathGenerator(self.tools.get("LLM"), self.tracer)

    def _record_task_short_name(self, task_id: str, short_name: Optional[str]) -> None:
        """Record or update a task's short name in the centralized map."""
        if task_id and short_name:
            self.task_short_name_map[task_id] = short_name

    # No sanitization: visualization will render names exactly as generated

    async def generate_short_names_for_pending_tasks(self, new_pending_tasks: List[PendingTask], current_task: Optional[Task] = None) -> None:
        """Use LLM in a single batch to generate unique, discriminative, short names for newly parsed tasks.

        The LLM considers existing short names and descriptions to avoid collisions and keep names concise.
        Updates each PendingTask.short_name in-place and records into task_short_name_map.
        """
        if not new_pending_tasks:
            return

        llm_tool = self.tools.get("LLM")
        if not llm_tool:
            return        

        # Prepare new task payload
        new_tasks_payload = [
            {"task_id": pt.task_id, "description": pt.description}
            for pt in new_pending_tasks
        ]

        # Build XML blocks to preserve newlines and avoid escaping issues
        existing_names_xml = "\n".join([f"<task><task_id>{task_id}</task_id><name>{sname}</name></task>" for task_id, sname in self.task_short_name_map.items() if sname])
        current_task_xml = (
            f"<task_id>{current_task.task_id}</task_id>\n<description>\n{current_task.description}\n</description>\n"
            f"<short_name>{current_task.short_name}</short_name>"
        ) if current_task else "<current_task/>"
        new_tasks_xml = "\n".join([
            f"<task>\n<task_id>{pt['task_id']}</task_id>\n<description>\n{pt['description']}\n</description>\n</task>"
            for pt in new_tasks_payload
        ])

        prompt = f"""
You're assigning compact, unique short names to newly generated tasks. Requirements:
- Ensure uniqueness across all existing short names
- Keep names discriminative and concise
- Use the same language as each task's description
- Keep names under 15 words
- You can change existing names if needed to ensure uniqueness

Use the XML blocks below. Do not include any markdown. Return only via the function call with assignments for ALL new tasks.

<existing_short_names>
{existing_names_xml}
</existing_short_names>

<current_task>
{current_task_xml}
</current_task>

<new_tasks>
{new_tasks_xml}
</new_tasks>
"""

        assign_names_tool = {
            "type": "function",
            "function": {
                "name": "assign_short_names",
                "description": "Assign unique, short names for tasks in one batch",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "assignments": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "task_id": {"type": "string"},
                                    "short_name": {"type": "string"}
                                },
                                "required": ["task_id", "short_name"]
                            }
                        }
                    },
                    "required": ["assignments"]
                }
            }
        }

        llm_response = await llm_tool.execute({
            "prompt": prompt,
            "tools": [assign_names_tool]
        })

        # Parse tool call assignments
        assignments: List[Dict[str, str]] = []
        if isinstance(llm_response, dict) and "tool_calls" in llm_response:
            for tool_call in llm_response["tool_calls"]:
                if tool_call.get("name") == "assign_short_names":
                    args = tool_call.get("arguments", {})
                    proposed = args.get("assignments")
                    if isinstance(proposed, str):
                        try:
                            proposed = json_repair.loads(proposed)
                        except Exception:
                            proposed = []
                    if isinstance(proposed, list):
                        assignments = [a for a in proposed if isinstance(a, dict) and "task_id" in a and "short_name" in a]
        # Fallback: if nothing usable, keep existing short names
        if not assignments:
            raise ValueError("LLM did not return assignments for short names")

        # Build a map from id to the returned name
        id_to_name = {a["task_id"]: a.get("short_name", "") for a in assignments if "task_id" in a}

        # Apply to pending tasks and record
        by_id = {pt.task_id: pt for pt in new_pending_tasks}
        for tid, sname in id_to_name.items():
            if tid in by_id:
                by_id[tid].short_name = sname
                self._record_task_short_name(tid, sname)
        # Record any remaining without assignment using their existing name
        for pt in new_pending_tasks:
            if pt.task_id not in id_to_name:
                self._record_task_short_name(pt.task_id, pt.short_name)
    
    def _get_engine_state(self) -> Dict[str, Any]:
        """Get current engine state for tracing"""
        return {
            "task_stack": [asdict(task) for task in self.task_stack],
            "context": json.loads(json.dumps(self.context)),  # Deep copy
            "task_execution_counter": self.task_execution_counter,
            "last_task_output": self.last_task_output
        }
    
    def register_tool(self, tool: BaseTool) -> None:
        """Register a new tool instance
        
        Args:
            tool: Instance of a tool that inherits from BaseTool
        """
        if not isinstance(tool, BaseTool):
            raise TypeError(f"Tool must inherit from BaseTool, got {type(tool)}")
        
        self.tools[tool.tool_id] = tool
        print(f"[TOOL_REGISTRY] Registered tool: {tool.tool_id}")
    
    def get_available_tools(self) -> Dict[str, str]:
        """Get a list of available tools and their types
        
        Returns:
            Dictionary mapping tool_id to tool class name
        """
        return {tool_id: tool.__class__.__name__ for tool_id, tool in self.tools.items()}
    
    def get_last_task_output(self) -> Any:
        """Get the output of the last executed task
        
        Returns:
            The output from the most recently executed task, or None if no tasks have been executed
        """
        return self.last_task_output
    
    def load_context(self, load_if_exists=True) -> Dict[str, Any]:
        """Load context from file or initialize empty"""
        if load_if_exists and self.context_file.exists():
            with open(self.context_file, 'r', encoding='utf-8') as f:
                self.context = json.load(f)
        else:
            self.context = {}
        return self.context
    
    def save_context(self):
        """Save context to file"""
        with open(self.context_file, 'w', encoding='utf-8') as f:
            json.dump(self.context, f, ensure_ascii=False, indent=2)
    
    def load_sop_document(self, doc_id: str) -> SOPDocument:
        """Load and parse a SOP document by doc_id"""
        return self.sop_loader.load_sop_document(doc_id)
    
    def resolve_json_path(self, path: str, context: Dict[str, Any]) -> Any:
        """JSON path resolver using jsonpath_ng library"""
        try:
            jsonpath_expr = parse(path)
            matches = jsonpath_expr.find(context)
            if matches:
                return matches[0].value
            else:
                return None
        except Exception as e:
            print(f"Warning: Failed to resolve JSON path '{path}': {e}")
            return None
    
    def render_template(self, template: str, variables: Dict[str, Any]) -> str:
        """Render template with variables using {var} syntax"""
        for key, value in variables.items():
            template = template.replace(f"{{{key}}}", str(value))
        return template
    
    def add_execution_prefix_to_path(self, json_path: str) -> str:
        """Add execution counter prefix to JSON path
        
        Args:
            json_path: Original JSON path like '$.messages[0]' or '$.output'
            
        Returns:
            JSON path with execution prefix like '$.msg1_messages[0]' or '$.msg1_output'
        """
        if not json_path or not json_path.startswith('$.'):
            return json_path
            
        # Extract the first level key after '$.'
        # Handle cases like: $.key, $.key[0], $.key.subkey, etc.
        parts = json_path[2:].split('.', 1)  # Remove '$.' and split on first '.'
        if not parts[0]:
            return json_path
            
        # Extract the key name (before any brackets)
        first_key = parts[0].split('[')[0]
        
        # Create prefixed key
        prefixed_key = f"msg{self.task_execution_counter}_{first_key}"
        
        # Rebuild the path
        if '[' in parts[0]:  # Handle array notation like 'key[0]'
            bracket_part = parts[0][len(first_key):]
            new_first_part = prefixed_key + bracket_part
        else:
            new_first_part = prefixed_key
            
        if len(parts) > 1:  # Has additional parts after first dot
            return f"$.{new_first_part}.{parts[1]}"
        else:
            return f"$.{new_first_part}"
    
    async def create_task_from_sop(self, sop_doc: SOPDocument, pending_task: PendingTask) -> Task:
        """Create a task from a SOP document and PendingTask"""

        # Generate input JSON paths if not provided but input_description exists, iterate through input_description and see if the fields has path defined.
        input_json_path = sop_doc.input_json_path
        input_description_to_generate_path = {}
        for field, field_description in sop_doc.input_description.items():
            if not input_json_path.get(field):
                input_description_to_generate_path[field] = field_description

        if input_description_to_generate_path:
            print(f"[TASK_CREATION] Generating input JSON paths for {sop_doc.doc_id}, {input_description_to_generate_path}")
            update_input_json_path = await self.json_path_generator.generate_input_json_paths(
                input_description_to_generate_path,
                self.context,
                pending_task.description
            )
            input_json_path.update(update_input_json_path)

        # For output, we now defer generation until after tool execution if we have output_description
        output_json_path = sop_doc.output_json_path
        output_description = sop_doc.output_description
        
        return Task(
            task_id=pending_task.task_id,
            description=pending_task.description,
            short_name=pending_task.short_name,
            parent_task_id=pending_task.parent_task_id,
            sop_doc_id=sop_doc.doc_id,
            tool=sop_doc.tool,
            input_json_path=input_json_path,
            output_json_path=output_json_path,
            output_description=output_description
        )
    
    async def create_task_from_description(self, pending_task: PendingTask) -> Task:
        """Create a task from a PendingTask with enhanced relationship tracking
        
        This is the main interface for creating tasks from natural language.
        Steps:
        1. Parse sop_doc_id from description using patterns/LLM
        2. Search for SOP documents if sop_doc_id not in the description or sop_doc_id not exists.
        3. Load SOP document by sop_doc_id
        4. Create task with all fields populated from SOP
        """

        # Trace SOP resolution phase
        with self.tracer.trace_phase_with_data("sop_resolution") as phase_ctx:
            self.context["current_task"] = pending_task.description
            
            # Step 1: Parse sop_doc_id from natural language
            sop_doc_id = await self.sop_parser.parse_sop_doc_id_from_description(pending_task.description)

            if not sop_doc_id:
                # Use general fallback SOP document if no specific doc_id found
                print("[TASK_CREATION] No specific SOP document found, using fallback SOP document")
                sop_doc_id = "general/fallback"
            
            # Step 3: Load SOP document
            try:
                sop_doc = self.load_sop_document(sop_doc_id)
            except FileNotFoundError:
                raise ValueError(f"Cannot find SOP document for parsed doc_id: {sop_doc_id}")
            
            # Set phase data with results
            phase_ctx.set_data({
                "input": {"description": pending_task.description, "pending_task": asdict(pending_task)},
                "selected_doc_id": sop_doc_id,
                "loaded_sop_document": asdict(sop_doc)
            })
        
        # Start task creation phase
        with self.tracer.trace_phase_with_data("task_creation") as phase_ctx:
            # Step 4: Create task with all fields populated
            task = await self.create_task_from_sop(sop_doc, pending_task)
            # Keep short name map in sync
            self._record_task_short_name(task.task_id, task.short_name)
            
            # Set phase data
            phase_ctx.set_data({
                "sop_document": asdict(sop_doc),
                "pending_task": asdict(pending_task),
                "created_task": asdict(task)
            })
        
        print(f"[TASK_CREATION] Created task: {task.description}")
        print(f"                Task ID: {task.task_id}")
        print(f"                Short name: {task.short_name}")
        print(f"                Parent task ID: {task.parent_task_id}")
        print(f"                SOP doc: {task.sop_doc_id}")
        print(f"                Tool: {task.tool.get('tool_id', 'N/A')}")
        print(f"                Input JSON paths: {task.input_json_path}")
        print(f"                Output JSON path: {task.output_json_path}")
        print(f"                Output description: {task.output_description}")
        print(f"                Context: {json.dumps(self.context, ensure_ascii=False, indent=2)}")
        
        return task
    
    async def execute_task(self, task: Task) -> List[PendingTask]:
        """Execute a single task"""
        # Increment task execution counter
        self.task_execution_counter += 1
        
        print(f"\n=== Executing Task #{self.task_execution_counter}: {task.description} ===")
        print(f"SOP Doc: {task.sop_doc_id}")
        
        # Start task execution phase
        with self.tracer.trace_phase_with_data("task_execution") as phase_ctx:
            # Resolve input values from context
            input_values = {}
            for key, path in task.input_json_path.items():
                value = self.resolve_json_path(path, self.context)
                if value is None:
                    raise ValueError(f"Input path '{path}' not found in context: {self.context}")
                input_values[key] = value
                print(f"input {key}: {value}")
            
            # Prepare tool parameters
            tool_params = task.tool.get('parameters', {}).copy()
            
            # Render all string parameters with input values
            for param_key, param_value in tool_params.items():
                if isinstance(param_value, str):
                    tool_params[param_key] = self.render_template(param_value, input_values)

            # If input value key is not in tool_params, add it
            for key, value in input_values.items():
                if key not in tool_params:
                    tool_params[key] = value
                    print(f"Added task input parameter '{key}' with value to tools parameters as default value: {value}")
            
            # Call the tool
            tool_id = task.tool.get('tool_id')
            if tool_id not in self.tools:
                raise ValueError(f"Unknown tool: {tool_id}")
            
            tool_instance = self.tools[tool_id]
            # Capture nested LLM calls during actual tool execution
            with self.tracer.trace_tool_execution_step():
                tool_output = await tool_instance.execute(tool_params)
            print(f"Tool output: {tool_output}")
            
            # Set phase data with results
            phase_ctx.set_data({
                "task": asdict(task),
                "input_resolution": {"resolved_inputs": input_values},
            })
        
        # Start context update phase
        with self.tracer.trace_phase_with_data("context_update") as phase_ctx:
            context_before = json.loads(json.dumps(self.context))  # Deep copy
            
            # Update context with output data using prefixed jsonpath
            updated_paths = []
            removed_temp_keys = []

            # Generate output JSON path dynamically if needed (after getting tool output)
            if not task.output_json_path and task.output_description:
                print(f"[TASK_EXECUTION] Generating output JSON path for {task.sop_doc_id} based on tool output")
                
                # Use output path generation tracing context manager
                with self.tracer.trace_output_path_generation_step() as output_ctx:
                    task.output_json_path = await self.json_path_generator.generate_output_json_path(
                        task.output_description,
                        self.context,
                        task.description,
                        tool_output
                    )
                    print(f"[TASK_EXECUTION] Generated output JSON path: {task.output_json_path}")
                    output_ctx.set_result(generated_path=task.output_json_path)
            
                    # Add execution prefix to output JSON path
                    prefixed_output_path = self.add_execution_prefix_to_path(task.output_json_path)
                    print(f"[TASK_EXECUTION] Using prefixed output path: {prefixed_output_path}")

                    output_ctx.set_result(prefixed_path=prefixed_output_path)
            else:
                prefixed_output_path = self.add_execution_prefix_to_path(task.output_json_path)

            # Set the tool output value to the context using the prefixed JSON path
            set_json_path_value(self.context, prefixed_output_path, tool_output)
            print(f"Updated context at path '{prefixed_output_path}' with output")
            updated_paths.append(prefixed_output_path)

            # Remove _temp_input_ * key from context
            temp_keys = [k for k in self.context.keys() if k.startswith("_temp_input_")]
            for key in temp_keys:
                del self.context[key]
                removed_temp_keys.append(key)

            # Record last task output
            self.last_task_output = tool_output
            self.context["last_task_output"] = tool_output
            print(f"[TASK_EXECUTION] Recorded last task output in context")

            # Set phase data with results
            phase_ctx.set_data({
                "context_before": context_before,
                "context_after": json.loads(json.dumps(self.context)),  # Deep copy
                "updated_paths": updated_paths,
                "removed_temp_keys": removed_temp_keys
            })
        
        # Start new task generation phase
        with self.tracer.trace_phase_with_data("new_task_generation") as phase_ctx:
            # Use new task generation context manager
            with self.tracer.trace_new_task_generation_step() as step_ctx:
                # Use LLM to check the output, see if there is new task needed.
                new_pending_tasks = await self.parse_new_tasks_from_output(tool_output, task, self.task_stack)

                # Always batch-generate short names for the new tasks
                if new_pending_tasks:
                    await self.generate_short_names_for_pending_tasks(new_pending_tasks, current_task=task)
                
                # Set results in context manager
                step_ctx.set_result(
                    generated_tasks=[asdict(pending_task) for pending_task in new_pending_tasks],
                    tool_output=tool_output,
                    task_description=task.description
                )
            
            # Set phase data with task generation results
            phase_ctx.set_data({
                "parent_task": asdict(task),
                "tool_output": tool_output,
                "current_task_description": task.description,
                "generated_tasks": [asdict(pending_task) for pending_task in new_pending_tasks]
            })

        return new_pending_tasks
    
    async def run_task(self, task: Task):
        """Run a single task and save context"""
        print(task)
        #input("Continue to execute task? Press Enter to continue...")
        new_task_list = await self.execute_task(task)
        self.save_context()
        return new_task_list

    async def add_new_tasks(self, new_pending_tasks: List[PendingTask]) -> None:
        """Add new task references to the task stack
        
        Args:
            new_pending_tasks: List of PendingTask objects to add to the stack
            
        Note:
            Tasks are added in reverse order so that the first task in the list
            is executed first (LIFO stack behavior)
        """
        if not new_pending_tasks:
            return
            
        # Add tasks in reverse order so first task is executed first
        for pending_task in reversed(new_pending_tasks):
            self.task_stack.append(pending_task)
            self.pending_tasks[pending_task.task_id] = pending_task
            # Record short name in central map
            self._record_task_short_name(pending_task.task_id, pending_task.short_name)
            print(f"[TASK_STACK] Added task to stack: {pending_task.short_name} (ID: {pending_task.task_id})")
        
        print(f"[TASK_STACK] Stack size: {len(self.task_stack)}")

    async def parse_new_tasks_from_output(self, output: Any, current_task: Task, task_stack: List[PendingTask]) -> List[PendingTask]:
        """Parse new task descriptions from tool output using LLM with function calling
        
        Args:
            output: The output from the previously executed task (any type, will be converted to string)
            current_task: The current Task object for context
            
        Returns:
            List of PendingTask objects extracted from the output. Empty list if no tasks found.
        """
        # Convert output to string
        if isinstance(output, dict):
            # Try to wrap each key using xml format, value as string
            output_str = "\n".join([f"<{k}>\n{v}\n</{k}>" for k, v in output.items()])
        else:
            output_str = str(output)

        # Use xml format to compact pending task description to string
        pending_task_list_str = "No tasks waiting in queue"
        if task_stack:
            pending_descriptions = []
            for pending in task_stack:
                pending_descriptions.append(f"<task>{pending.description}</task>")
            pending_task_list_str = "\n".join(pending_descriptions)

        # Create prompt for LLM to extract task descriptions
        prompt = f"""
An agent has completed a task from user, analyze the output of the following task and extract any new task descriptions that need to be executed by agent. If the output doesn't satisfy the current task requirement, generate tasks for agent to fix error on original one or finish the remaining task, the generated tasks should also contain the task to apply the fix to original content, so that user can get a complete result instead of multiple fragmented parts.

Please carefully analyze the output content and identify if it explicitly contains any follow-up tasks that explicitly needed to be executed by agent.

**Analysis process:**
1. Is the output satisfy the current task requirement?
2. Does the output indicate any follow-up tasks that explicitly needed to be executed by agent?
3. Any new task already covered by the task waiting for execute? If so, skip the duplicated task.

**Important notes:**
1. Only extract tasks that clearly need to be executed, do not speculate
2. Task descriptions should be clear and specific. Make sure the task is understandable without any additional context. Keep the reference documentation path as it is.
3. Ideally, we should have in the task description: 
 - Why we need to do this: include any context like the current task description and how current task raised new task.
 - What is the expected output: what format or deliverable we expect.
 - How to do it: if there is reference documentation, include the path to it.
4. There can be overlap between task description, make sure task description is comprehensive.
5. Please use the original task description's language as your response language.
6. If the output doesn't satisfy the current task requirement, you can add more context to the original task description to help avoid the error or missing part.

<Example which should output new task>

<Current task description>
We need to implement a landing page site for small business company. Draft a plan for implementation for agents to execute.
</Current task description>

<Task output content to analyze>
Agent should execute these tasks:
 - Follow user_communicate.md. Ask user for requirement on landing page, including layout, style, language.
 - Draft plan for frontend development.
 - Draft plan for backend development.
 - Implement frontend and backend site.
</Task output content to analyze>

<Task list waiting for execute>
<task>Follow the development plan and implement frontend and backend site.</task>
</Task list waiting for execute>

extract_new_tasks:
  think process: 
  
Let me analyze the task output to see if it contains explicit follow-up tasks:

1. Is the output satisfy the current task requirement?
The current task was to "Draft a plan for implementation for agents to execute" for a landing page site. The output does provide a high-level plan with 4 specific tasks that agents should execute, so it does satisfy the requirement.

2. Does the output indicate any follow-up tasks that explicitly needed to be executed by agent?
Yes, the output explicitly lists 4 tasks that "Agent should execute":
- Follow user_communicate.md. Ask user for requirement on landing page, including layout, style, language.
- Draft plan for frontend development.
- Draft plan for backend development.
- Implement frontend and backend site.

3. Any new task already covered by the task waiting for execute? If so, skip the duplicated task.
`Implement frontend and backend site.` is duplicate with the task waiting for execute. We should skip generate it as new task.

tasks:
[
  "Background: We are implementing a landing page site for small business company. We need to gather user requirements first.\n\nTask: Follow user_communicate.md documentation and ask user for requirements on landing page, including layout, style, and language preferences.\n\nExpected output: User answered preferred layout preferences, visual style guidelines, and language specifications for the landing page.",
  "Background: We are implementing a landing page site for small business company. In previous step, we gathered user requirements. In this step we need to create a detailed frontend development plan.\n\nTask: Draft a comprehensive plan for frontend development of the landing page site.\n\nExpected output: A detailed frontend development plan that includes technology stack, component structure, responsive design approach, and implementation timeline.",
  "Background: We are implementing a landing page site for small business company. In previous step, we gathered user requirements, created plan for frontend development. In this step, we need to plan the backend infrastructure and functionality.\n\nTask: Draft a comprehensive plan for backend development of the landing page site.\n\nExpected output: A detailed backend development plan including server architecture, database design (if needed), API endpoints, hosting requirements, and security considerations.",
]
</Example which should output new task>

<Example which should not output new task>

<Current task description>
We need to implement a landing page site for small business company. Draft a plan for implementation.
</Current task description>

<Task output content to analyze>
Here is a plan:
 - Follow user_communicate.md. Ask user for requirement on landing page, including layout, style, language.
 - Draft plan for frontend development.
 - Draft plan for backend development.
 - Implement frontend and backend site.
</Task output content to analyze>

<Task list waiting for execute>
No tasks waiting in queue
</Task list waiting for execute>

extract_new_tasks:
  think process: 

Let me analyze the task output step by step:

1. Is the output satisfy the current task requirement?
The current task was to "Draft a plan for implementation" of a landing page site for a small business company. The output provides a high-level plan with 4 bullet points covering user requirements gathering, frontend planning, backend planning, and implementation. This satisfies the requirement of drafting a plan.

2. Does the output indicate any follow-up tasks that explicitly needed to be executed by agent?
Looking at the output, I can see explicit tasks mentioned, but they are not intended for agent to execute. User just need a plan, but no need for agent.

tasks: []
</Example which should not output new task>

If you find new tasks that need to be executed, use the extract_new_tasks function to return them. If no new tasks are found, call the function with an empty task list.

Here is the task that needs analysis:
<Current task description>
{current_task.description}
</Current task description>

<Task output content to analyze>
{output_str}
</Task output content to analyze>

<Task list waiting for execute>
{pending_task_list_str}
</Task list waiting for execute>
"""

        # Define the function schema for extracting new tasks
        extract_tasks_tool = {
            "type": "function",
            "function": {
                "name": "extract_new_tasks",
                "description": "Extract new task descriptions that need to be executed by the agent",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "think_process": {
                            "type": "string",
                            "description": "The process of analyze if there is new task for agent to do."
                        },
                        "tasks": {
                            "type": "array",
                            "description": "List of new task descriptions that need to be executed, each task should be a valid json string, be careful when you escape newline and quotes \". Empty array if no new tasks found."
                        }
                    },
                    "required": ["tasks"]
                }
            }
        }

        llm_tool = self.tools.get("LLM")
        if not llm_tool:
            raise Exception("[TASK_PARSER] Warning: LLM tool not available, returning empty task list")

        llm_response = await llm_tool.execute({
            "prompt": prompt,
            "tools": [extract_tasks_tool]
        })
        print(f"[TASK_PARSER] LLM response: {llm_response}")
        
        # Handle both string and dict responses (tool calls)
        if isinstance(llm_response, dict) and "tool_calls" in llm_response:
            # Extract tasks from tool calls
            for tool_call in llm_response["tool_calls"]:
                if tool_call.get("name") == "extract_new_tasks":
                    task_list = tool_call.get("arguments", {}).get("tasks", [])
                    
                    # Validate that it's a list of strings
                    if isinstance(task_list, str):
                        task_list = json_repair.loads(task_list)
                        assert(isinstance(task_list, list))
                    elif not isinstance(task_list, list):
                        raise ValueError(f"[TASK_PARSER] Tool call response is not a list: {task_list}")
                    
                    validated_tasks = []
                    for task in task_list:
                        if isinstance(task, str) and task.strip():
                            validated_tasks.append(task.strip())
                        else:
                            print(f"[TASK_PARSER] Warning: Invalid task format: {task}")
                    
                    # Convert extracted task descriptions to PendingTask objects
                    pending_tasks = []
                    for task_description in validated_tasks:
                        pending_task = PendingTask(
                            description=task_description,
                            parent_task_id=current_task.task_id,
                            generated_by_phase="new_task_generation"
                            # task_id and short_name will be auto-generated
                        )
                        pending_tasks.append(pending_task)
                    
                    print(f"[TASK_PARSER] Extracted {len(pending_tasks)} new tasks: {[pt.short_name for pt in pending_tasks]}")
                    return pending_tasks
            
            # No tool calls found with the expected function name
            print("[TASK_PARSER] No extract_new_tasks tool call found, returning empty task list")
            return []
        else:
            # Fallback: No tool calls were made, assume no new tasks
            print("[TASK_PARSER] No tool calls in response, returning empty task list")
            return []

    async def generate_recovery_task(self, missing_error: TaskInputMissingError, task_description: str, parent_task_id: str = None) -> PendingTask:
        """Generate a recovery task to obtain missing input
        
        Args:
            missing_error: The TaskInputMissingError that was raised
            task_description: The original task description that failed
            parent_task_id: Optional parent task ID for relationship tracking
            
        Returns:
            A PendingTask that can be used to gather the missing information
        """
        prompt = f"""
Some information seems missing or not clarified for following task. Please generate a task to generate or obtain necessary information.

## Input Missing Task:
{task_description}

## Missing Information:
- Field name: {missing_error.field_name}
- Field description: {missing_error.description}

## Current Available Information:
{yaml.dump(self.context, allow_unicode=True, indent=2)}

## Objective:
Generate a clear, specific task description that would help obtain the missing information described in the field description. 

The task should:

1. Clearly explain what information is needed and why. Only include necessary information for the task.
2. If the information must task some user input, eg. It needs user's name / preference / drug history. Use pattern like: 'Use user_communicate.md to ask user "xxxxx"'.
3. If the information can be generated by large language model, then use pattern like 'Use llm.md, prompt is:\n "xxxxx"'.
4. If the information can be obtained by cli tool, then use pattern like 'Use bash.md, command is: `xxxxx`'.

## Missing Information:

Please return only the task description as a single paragraph, without additional formatting or explanations.
"""
        
        llm_tool = self.tools.get("LLM")
        recovery_response = await llm_tool.execute({"prompt": prompt})
        
        # Extract content from new response format
        recovery_task_description = recovery_response["content"].strip()
        
        # Create and return PendingTask
        recovery_pending_task = PendingTask(
            description=recovery_task_description,
            parent_task_id=parent_task_id,
            generated_by_phase="recovery_task_generation"
        )
        
        return recovery_pending_task

    async def start(self, initial_task_description: str = None) -> None:
        """Start the execution engine with an optional initial task
        
        Args:
            initial_task_description: Optional initial task to start with
            
        The engine will:
        1. Add the initial task to the stack if provided
        2. Continuously pop tasks from the stack and execute them
        3. Add any new tasks generated during execution back to the stack
        4. Continue until the stack is empty
        """
        print("[ENGINE] Starting execution engine...")
        
        # Start tracing session using context manager
        with self.tracer.trace_session(initial_task_description, engine_state_provider=self._get_engine_state):
            # Add initial task to stack if provided
            if initial_task_description:
                initial_pending_task = PendingTask(
                    description=initial_task_description
                    # task_id, short_name auto-generated, parent_task_id remains None for root task
                )
                self.task_stack.append(initial_pending_task)
                self.pending_tasks[initial_pending_task.task_id] = initial_pending_task
                self._record_task_short_name(initial_pending_task.task_id, initial_pending_task.short_name)
                print(f"[ENGINE] Added initial task: {initial_pending_task.short_name} (ID: {initial_pending_task.task_id})")
            
            # Main execution loop
            while self.task_stack:
                # Pop the next task from the stack
                pending_task = self.task_stack.pop()
                print(f"\n[ENGINE] Processing task from stack: {pending_task.short_name} (ID: {pending_task.task_id})")
                print(f"[ENGINE] Remaining tasks in stack: {len(self.task_stack)}")
                
                # Use context-managed task execution tracing
                with self.tracer.trace_task_execution(pending_task, engine_state_provider=self._get_engine_state) as task_ctx:
                    try:
                        # Create task object from PendingTask
                        task = await self.create_task_from_description(pending_task)
                        # Execute the task
                        new_pending_tasks = await self.run_task(task)
                        # Clear retry count on successful execution
                        if pending_task.task_id in self.task_retry_count:
                            del self.task_retry_count[pending_task.task_id]
                        # Add any new tasks to the stack
                        if new_pending_tasks:
                            await self.add_new_tasks(new_pending_tasks)
                        # Success path; no explicit status needed (defaults to COMPLETED)
                    except TaskInputMissingError as e:
                        print(f"[ENGINE] Task creation failed due to missing input: {e}")

                        # Check retry count (using task_id as key)
                        retry_count = self.task_retry_count.get(pending_task.task_id, 0)
                        if retry_count >= self.max_retries:
                            task_ctx.set_status(ExecutionStatus.FAILED, e)
                            raise TaskCreationError(task_description=pending_task.description, original_error=TaskInputMissingError)

                        # Increment retry count
                        self.task_retry_count[pending_task.task_id] = retry_count + 1

                        # Put the original task back on the stack (it will be retried after recovery)
                        self.task_stack.append(pending_task)
                        print(f"[ENGINE] Put failed task back on stack (attempt {retry_count + 1}/{self.max_retries}): {pending_task.short_name}")

                        # Generate and add recovery task to the top of the stack (it will be executed first)
                        recovery_pending_task = await self.generate_recovery_task(e, pending_task.description, pending_task.task_id)
                        self.task_stack.append(recovery_pending_task)
                        self.pending_tasks[recovery_pending_task.task_id] = recovery_pending_task
                        print(f"[ENGINE] Added recovery task to stack: {recovery_pending_task.short_name} (ID: {recovery_pending_task.task_id})")
                        # Mark as retrying for this execution
                        task_ctx.set_status(ExecutionStatus.RETRYING, e)
        
            print("[ENGINE] All tasks completed. Execution engine stopped.")

async def main():
    """Execute the blog outline generation document"""
    # Initialize the engine
    engine = DocExecuteEngine()
    
    # Load context (or start fresh)
    engine.load_context(load_if_exists=False)
    
    
    #task_description = "Follow write_xiaohongshu_ganhuo.md, 为一个初中男语文老师写关于作文的小红书笔记，对象是希望自己孩子作文能写好的家长，目的是推广他的作文精批服务。"

    task_description = "用 az cli 创建一个新的 aks arc cluster"

    # Execute the task
    print("Executing...")
    result = await engine.start(task_description)
    
    # Display results
    print("\n=== Execution Complete ===")
    print(f"Result: {json.dumps(result, ensure_ascii=False, indent=2)}")
    
    # Display context for debugging
    print("\n=== Context ===")
    print(json.dumps(engine.context, ensure_ascii=False, indent=2))

    # Save context for future use
    engine.save_context()
    
    return result

if __name__ == "__main__":
    asyncio.run(main())
