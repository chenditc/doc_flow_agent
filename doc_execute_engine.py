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

import yaml
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from sop_document import SOPDocument, SOPDocumentLoader, SOPDocumentParser
from tools import BaseTool, LLMTool, CLITool, UserCommunicateTool
from tools.json_path_generator import JsonPathGenerator
import jsonpath_ng
from jsonpath_ng.ext import parse
from utils import set_json_path_value
from exceptions import TaskInputMissingError, TaskCreationError
from tracing import ExecutionTracer, ExecutionStatus
from tracing_wrappers import TracingToolWrapper, TracingLLMTool


@dataclass
class Task:
    """A task to be executed"""
    task_id: str
    description: str
    sop_doc_id: str
    tool: Dict[str, Any]
    input_json_path: Dict[str, str]
    output_json_path: str  # Changed from Dict[str, str] to str - now holds jsonpath
    output_description: str = None  # Store output description for dynamic path generation

    def __str__(self):
        # Return all fields as a formatted string for easy logging
        return (f"Task ID: {self.task_id}\n"
                f"Description: {self.description}\n"
                f"SOP Document ID: {self.sop_doc_id}\n"
                f"Tool: {self.tool.get('tool_id', 'N/A')}\n"
                f"Input JSON Paths: {json.dumps(self.input_json_path, ensure_ascii=False)}\n"
                f"Output JSON Path: {self.output_json_path}\n"
                f"Output Description: {self.output_description}")
    
    def __repr__(self):
        # Return a concise representation for debugging
        return (f"Task(task_id={self.task_id}, description={self.description}, "
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
        self.task_stack = []  # Stack of task description strings
        self.task_execution_counter = 0  # Counter for executed tasks
        self.task_retry_count = {}  # Track retry attempts for failed tasks
        self.max_retries = 3  # Maximum retry attempts per task
        self.last_task_output = None  # Store the last task output
        
        # Initialize tracing
        self.tracer = ExecutionTracer(output_dir=trace_output_dir, enabled=enable_tracing)
        
        # Initialize tools as instances of tool classes
        base_tools = {
            "LLM": LLMTool(),
            "CLI": CLITool(),
            "USER_COMMUNICATE": UserCommunicateTool()
        }
        
        # Wrap tools with tracing if enabled
        if enable_tracing:
            self.tools = {
                "LLM": TracingLLMTool(base_tools["LLM"], self.tracer),
                "CLI": TracingToolWrapper(base_tools["CLI"], self.tracer),
                "USER_COMMUNICATE": TracingToolWrapper(base_tools["USER_COMMUNICATE"], self.tracer)
            }
        else:
            self.tools = base_tools
        
        # Initialize SOPDocument components
        self.sop_loader = SOPDocumentLoader(docs_dir)
        self.sop_parser = SOPDocumentParser(docs_dir, llm_tool=self.tools.get("LLM"))
        
        # Initialize JSON path generator
        self.json_path_generator = JsonPathGenerator(self.tools.get("LLM"))
    
    def _get_engine_state(self) -> Dict[str, Any]:
        """Get current engine state for tracing"""
        return {
            "task_stack": self.task_stack.copy(),
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
    
    async def create_task_from_sop(self, sop_doc: SOPDocument, description: str = None) -> Task:
        """Create a task from a SOP document"""

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
                description
            )
            input_json_path.update(update_input_json_path)

        # For output, we now defer generation until after tool execution if we have output_description
        output_json_path = sop_doc.output_json_path
        output_description = sop_doc.output_description
        
        return Task(
            task_id=str(uuid.uuid4()),
            description=description if description else sop_doc.description,
            sop_doc_id=sop_doc.doc_id,
            tool=sop_doc.tool,
            input_json_path=input_json_path,
            output_json_path=output_json_path,
            output_description=output_description
        )
    
    async def create_task_from_description(self, description: str) -> Task:
        """Create a task from natural language description
        
        This is the main interface for creating tasks from natural language.
        Steps:
        1. Parse sop_doc_id from description using patterns/LLM
        2. Search for SOP documents if sop_doc_id not in the description or sop_doc_id not exists.
        3. Load SOP document by sop_doc_id
        4. Create task with all fields populated from SOP
        """

        # Trace SOP resolution phase
        self.tracer.start_phase("sop_resolution")
        
        self.context["current_task"] = description
        
        # Step 1: Parse sop_doc_id from natural language
        sop_doc_id = await self.sop_parser.parse_sop_doc_id_from_description(description, self.tracer)

        if not sop_doc_id:
            # Use general fallback SOP document if no specific doc_id found
            print("[TASK_CREATION] No specific SOP document found, using fallback SOP document")
            sop_doc_id = "general/fallback"
        
        # Step 3: Load SOP document
        try:
            sop_doc = self.load_sop_document(sop_doc_id)
        except FileNotFoundError:
            self.tracer.end_phase(error=FileNotFoundError(f"Cannot find SOP document for parsed doc_id: {sop_doc_id}"))
            raise ValueError(f"Cannot find SOP document for parsed doc_id: {sop_doc_id}")
        
        # End SOP resolution phase with results
        sop_resolution_data = {
            "input": {"description": description},
            "selected_doc_id": sop_doc_id,
            "loaded_sop_document": asdict(sop_doc)
        }
        self.tracer.end_phase(sop_resolution_data)
        
        # Start task creation phase
        self.tracer.start_phase("task_creation")
        
        # Step 4: Create task with all fields populated
        task = await self.create_task_from_sop(sop_doc, description)
        
        # End task creation phase
        task_creation_data = {
            "sop_document": asdict(sop_doc),
            "created_task": asdict(task)
        }
        self.tracer.end_phase(task_creation_data)
        
        print(f"[TASK_CREATION] Created task: {task.description}")
        print(f"                SOP doc: {task.sop_doc_id}")
        print(f"                Tool: {task.tool.get('tool_id', 'N/A')}")
        print(f"                Input JSON paths: {task.input_json_path}")
        print(f"                Output JSON path: {task.output_json_path}")
        print(f"                Output description: {task.output_description}")
        print(f"                Context: {json.dumps(self.context, ensure_ascii=False, indent=2)}")
        
        return task
    
    async def execute_task(self, task: Task) -> List[str]:
        """Execute a single task"""
        # Increment task execution counter
        self.task_execution_counter += 1
        
        print(f"\n=== Executing Task #{self.task_execution_counter}: {task.description} ===")
        print(f"SOP Doc: {task.sop_doc_id}")
        
        # Start task execution phase
        self.tracer.start_phase("task_execution")
        
        # Resolve input values from context
        input_values = {}
        for key, path in task.input_json_path.items():
            value = self.resolve_json_path(path, self.context)
            if value is None:
                self.tracer.end_phase(error=ValueError(f"Input path '{path}' not found in context"))
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
            self.tracer.end_phase(error=ValueError(f"Unknown tool: {tool_id}"))
            raise ValueError(f"Unknown tool: {tool_id}")
        
        tool_instance = self.tools[tool_id]
        try:
            tool_output = await tool_instance.execute(tool_params)
            print(f"Tool output: {tool_output}")
        except Exception as e:
            self.tracer.end_phase(error=e)
            raise
        
        # Generate output JSON path dynamically if needed (after getting tool output)
        if not task.output_json_path and task.output_description:
            print(f"[TASK_EXECUTION] Generating output JSON path for {task.sop_doc_id} based on tool output")
            task.output_json_path = await self.json_path_generator.generate_output_json_path(
                task.output_description,
                self.context,
                task.description,
                tool_output
            )
            print(f"[TASK_EXECUTION] Generated output JSON path: {task.output_json_path}")
        
        # Add execution prefix to output JSON path
        if task.output_json_path:
            prefixed_output_path = self.add_execution_prefix_to_path(task.output_json_path)
            print(f"[TASK_EXECUTION] Using prefixed output path: {prefixed_output_path}")
        else:
            prefixed_output_path = None
        
        # End task execution phase with results
        task_execution_data = {
            "task": asdict(task),
            "input_resolution": {"resolved_inputs": input_values},
            "generated_path": task.output_json_path,
            "prefixed_path": prefixed_output_path
        }
        self.tracer.end_phase(task_execution_data)
        
        # Start context update phase
        self.tracer.start_phase("context_update")
        context_before = json.loads(json.dumps(self.context))  # Deep copy
        
        # Update context with output data using prefixed jsonpath
        updated_paths = []
        removed_temp_keys = []
        
        if prefixed_output_path:
            try:
                # Set the tool output value to the context using the prefixed JSON path
                set_json_path_value(self.context, prefixed_output_path, tool_output)
                print(f"Updated context at path '{prefixed_output_path}' with output")
                updated_paths.append(prefixed_output_path)
            except Exception as e:
                print(f"Warning: Failed to update context at path '{prefixed_output_path}': {e}")
                self.tracer.end_phase(error=e)
                raise

        # Remove _temp_input_ * key from context
        temp_keys = [k for k in self.context.keys() if k.startswith("_temp_input_")]
        for key in temp_keys:
            del self.context[key]
            removed_temp_keys.append(key)

        # Record last task output
        self.last_task_output = tool_output
        self.context["last_task_output"] = tool_output
        print(f"[TASK_EXECUTION] Recorded last task output in context")

        # End context update phase
        context_update_data = {
            "context_before": context_before,
            "context_after": json.loads(json.dumps(self.context)),  # Deep copy
            "updated_paths": updated_paths,
            "removed_temp_keys": removed_temp_keys
        }
        self.tracer.end_phase(context_update_data)
        
        # Start new task generation phase
        self.tracer.start_phase("new_task_generation")
        
        # Use LLM to check the output, see if there is new task needed.
        try:
            new_task_list = await self.parse_new_tasks_from_output(tool_output, task.description)
        except Exception as e:
            self.tracer.end_phase(error=e)
            raise
        
        # End new task generation phase
        new_task_generation_data = {
            "tool_output": tool_output,
            "current_task_description": task.description,
            "generated_tasks": new_task_list
        }
        self.tracer.end_phase(new_task_generation_data)

        return new_task_list
    
    async def run_task(self, task: Task):
        """Run a single task and save context"""
        print(task)
        #input("Continue to execute task? Press Enter to continue...")
        new_task_list = await self.execute_task(task)
        self.save_context()
        return new_task_list

    async def add_new_tasks(self, new_tasks: List[str]) -> None:
        """Add new tasks to the task stack
        
        Args:
            new_tasks: List of task description strings to add to the stack
            
        Note:
            Tasks are added in reverse order so that the first task in the list
            is executed first (LIFO stack behavior)
        """
        if not new_tasks:
            return
            
        # Add tasks in reverse order so first task is executed first
        for task_description in reversed(new_tasks):
            self.task_stack.append(task_description)
            print(f"[TASK_STACK] Added task to stack: {task_description}")
        
        print(f"[TASK_STACK] Stack size: {len(self.task_stack)}")

    async def parse_new_tasks_from_output(self, output: Any, current_task_description: str) -> List[str]:
        """Parse new task descriptions from tool output using LLM
        
        Args:
            output: The output from the previously executed task (any type, will be converted to string)
            current_task_description: Description of the current task for context
            
        Returns:
            List of task descriptions extracted from the output. Empty list if no tasks found.
        """
        # Convert output to string
        output_str = str(output)
        
        # Create prompt for LLM to extract task descriptions
        prompt = f"""
An agent has completed a task from user, analyze the output of the following task and extract any new task descriptions that need to be executed by agent.

<Current task description>
{current_task_description}
</Current task description>

<Task output content>
{output_str}
</Task output content>

Please carefully analyze the output content and identify if it explicitly contains any follow-up tasks that explicitly needed to be executed by agent. Only return the explicit task, do not infer task by yourself. If there are explicitly stated new tasks for agent, please return them in the following json format:

**Format requirements:**
- If no new tasks, return:
<THINK_PROCESS>
1. Is the output satisfy the current task requirement?
2. Does the output indicate any follow-up tasks that explicitly needed to be executed by agent?
</THINK_PROCESS>
<FINAL_CONFLUSION>
```json
[]
```
</FINAL_CONFLUSION>

- If new tasks exist, return JSON array format: 
<THINK_PROCESS>
1. Is the output satisfy the current task requirement?
2. Does the output indicate any follow-up tasks that explicitly needed to be executed by agent?
</THINK_PROCESS>
<FINAL_CONFLUSION>
```json
["task description 1", "task description 2", ...]
```
</FINAL_CONCLUSION>

**Example Return:**


**Important notes:**
1. Only extract tasks that clearly need to be executed, do not speculate
2. Task descriptions should be clear and specific, include any background information if needed. Make sure the task is understandable without additional context. Keep the reference documentation path as it is.
3. Ideally, we should have in the task description: 
 - Why we need to do this: include any context like the current task description and how current task raised new task.
 - What is the expected output: what format or deliverable we expect.
 - How to do it: if there is reference documentation, include the path to it.
4. There can be overlap between task description, make sure task description is comprehensive.
5. You can use the original task description's language as your response language.

Please return the JSON array directly without any additional explanations.
"""        
        # Use LLM tool to analyze output and extract tasks

        llm_tool = self.tools.get("LLM")
        if not llm_tool:
            raise Exception("[TASK_PARSER] Warning: LLM tool not available, returning empty task list")

        llm_response = await llm_tool.execute({
            "prompt": prompt,
            "step": "new_task_generation"
        })
        print(f"[TASK_PARSER] LLM response: {llm_response}")
        
        # Parse the JSON response
        import json
        # Match content btween ```json and ```
        json_match = re.search(r'```json(.*?)```', llm_response, re.DOTALL)
        if json_match:
            llm_response = json_match.group(1)
        else:
            raise Exception(f"[TASK_PARSER] Warning: LLM response does not match expected JSON array format: {llm_response}")
        
        # Try to parse as JSON array
        task_list = json.loads(llm_response.strip())
        
        # Validate that it's a list of strings
        if not isinstance(task_list, list):
            raise ValueError(f"[TASK_PARSER] LLM response is not a list: {llm_response}")
        
        validated_tasks = []
        for task in task_list:
            if isinstance(task, str) and task.strip():
                validated_tasks.append(task.strip())
            else:
                print(f"[TASK_PARSER] Warning: Invalid task format: {task}")
        
        print(f"[TASK_PARSER] Extracted {len(validated_tasks)} new tasks: {validated_tasks}")
        return validated_tasks

    async def generate_recovery_task(self, missing_error: TaskInputMissingError, task_description: str) -> str:
        """Generate a recovery task to obtain missing input
        
        Args:
            missing_error: The TaskInputMissingError that was raised
            task_description: The original task description that failed
            
        Returns:
            A task description that can be used to gather the missing information
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
        recovery_task = await llm_tool.execute({"prompt": prompt})
        return recovery_task.strip()

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
        
        # Start tracing session
        session_id = self.tracer.start_session(initial_task_description)
        self.tracer.capture_engine_state("start", self.task_stack, self.context, self.task_execution_counter)
        
        try:
            # Add initial task to stack if provided
            if initial_task_description:
                self.task_stack.append(initial_task_description)
                print(f"[ENGINE] Added initial task: {initial_task_description}")
            
            # Main execution loop
            while self.task_stack:
                # Pop the next task from the stack
                task_description = self.task_stack.pop()
                print(f"\n[ENGINE] Processing task from stack: {task_description}")
                print(f"[ENGINE] Remaining tasks in stack: {len(self.task_stack)}")
                
                # Start task execution tracing
                execution_id = self.tracer.start_task_execution(task_description, self._get_engine_state())
                
                try:
                    # Create task object from description
                    task = await self.create_task_from_description(task_description)
                    
                    # Execute the task
                    new_tasks = await self.run_task(task)
                    
                    # Clear retry count on successful execution
                    if task_description in self.task_retry_count:
                        del self.task_retry_count[task_description]
                    
                    # Add any new tasks to the stack
                    if new_tasks:
                        await self.add_new_tasks(new_tasks)
                    
                    # End successful task execution
                    self.tracer.end_task_execution(self._get_engine_state(), ExecutionStatus.COMPLETED)
                        
                except TaskInputMissingError as e:
                    print(f"[ENGINE] Task creation failed due to missing input: {e}")
                    
                    # Check retry count
                    retry_count = self.task_retry_count.get(task_description, 0)
                    if retry_count >= self.max_retries:
                        self.tracer.end_task_execution(self._get_engine_state(), ExecutionStatus.FAILED, e)
                        raise TaskCreationError(task_description=task_description, original_error=TaskInputMissingError)
                    
                    # Increment retry count
                    self.task_retry_count[task_description] = retry_count + 1
                    
                    # Put the original task back on the stack (it will be retried after recovery)
                    self.task_stack.append(task_description)
                    print(f"[ENGINE] Put failed task back on stack (attempt {retry_count + 1}/{self.max_retries}): {task_description}")
                    
                    # Generate and add recovery task to the top of the stack (it will be executed first)
                    try:
                        recovery_task = await self.generate_recovery_task(e, task_description)
                        self.task_stack.append(recovery_task)
                        print(f"[ENGINE] Added recovery task to stack: {recovery_task}")
                        
                        # End with retry status
                        self.tracer.end_task_execution(self._get_engine_state(), ExecutionStatus.RETRYING, e)
                    except Exception as recovery_error:
                        print(f"[ENGINE] Failed to generate recovery task: {recovery_error}")
                        self.tracer.end_task_execution(self._get_engine_state(), ExecutionStatus.FAILED, recovery_error)
                        raise TaskCreationError(task_description=task_description, original_error=recovery_error)      
                                      
                except Exception as e:
                    print(f"[ENGINE] Unexpected error executing task '{task_description}': {e}")
                    self.tracer.end_task_execution(self._get_engine_state(), ExecutionStatus.FAILED, e)
                    raise e
            
            print("[ENGINE] All tasks completed. Execution engine stopped.")
            
            # Capture final engine state and end session
            self.tracer.capture_engine_state("end", self.task_stack, self.context, self.task_execution_counter)
            trace_file = self.tracer.end_session(ExecutionStatus.COMPLETED)
            
        except Exception as e:
            # End session with error status
            self.tracer.capture_engine_state("error", self.task_stack, self.context, self.task_execution_counter)
            self.tracer.end_session(ExecutionStatus.FAILED)
            raise

async def main():
    """Execute the blog outline generation document"""
    # Initialize the engine
    engine = DocExecuteEngine()
    
    # Load context (or start fresh)
    engine.load_context(load_if_exists=False)
    
    
    task_description = "Follow bash.md, check current Beijing time"

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
