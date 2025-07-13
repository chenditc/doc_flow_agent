#!/usr/bin/env python3
"""
Execution Tracing System for Doc Execute Engine
Provides observability and replay capabilities for task execution
"""

import json
import uuid
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Union
from pathlib import Path
from enum import Enum


class ExecutionStatus(Enum):
    """Status of execution phases and tasks"""
    STARTED = "started"
    COMPLETED = "completed"
    FAILED = "failed"
    INTERRUPTED = "interrupted"
    RETRYING = "retrying"


@dataclass
class LLMCall:
    """Represents a single LLM interaction"""
    tool_call_id: str
    step: Optional[str]
    prompt: str
    response: str
    start_time: str
    end_time: str
    model: Optional[str] = None
    token_usage: Optional[Dict[str, int]] = None


@dataclass
class ToolCall:
    """Represents a tool execution"""
    tool_call_id: str
    tool_id: str
    parameters: Dict[str, Any]
    output: Any
    start_time: str
    end_time: str
    status: ExecutionStatus = ExecutionStatus.COMPLETED
    error: Optional[str] = None


@dataclass
class SopResolutionPhase:
    """SOP document resolution phase"""
    start_time: str
    end_time: Optional[str] = None
    status: ExecutionStatus = ExecutionStatus.STARTED
    input: Optional[Dict[str, Any]] = None
    candidate_documents: Optional[List[str]] = None
    llm_validation_call: Optional[LLMCall] = None
    selected_doc_id: Optional[str] = None
    loaded_sop_document: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


@dataclass
class JsonPathGeneration:
    """JSON path generation for a single input field"""
    field_name: str
    description: str
    llm_calls: List[LLMCall] = field(default_factory=list)
    generated_path: Optional[str] = None
    extracted_value: Any = None
    error: Optional[str] = None


@dataclass
class TaskCreationPhase:
    """Task creation phase"""
    start_time: str
    end_time: Optional[str] = None
    status: ExecutionStatus = ExecutionStatus.STARTED
    sop_document: Optional[Dict[str, Any]] = None
    json_path_generation: Dict[str, JsonPathGeneration] = field(default_factory=dict)
    output_path_generation: Optional[LLMCall] = None
    created_task: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


@dataclass
class TaskExecutionPhase:
    """Task execution phase"""
    start_time: str
    end_time: Optional[str] = None
    status: ExecutionStatus = ExecutionStatus.STARTED
    task: Optional[Dict[str, Any]] = None
    input_resolution: Optional[Dict[str, Any]] = None
    tool_execution: Optional[ToolCall] = None
    output_path_generation: Optional[LLMCall] = None
    generated_path: Optional[str] = None
    prefixed_path: Optional[str] = None
    error: Optional[str] = None


@dataclass
class ContextUpdatePhase:
    """Context update phase"""
    start_time: str
    end_time: Optional[str] = None
    status: ExecutionStatus = ExecutionStatus.STARTED
    context_before: Optional[Dict[str, Any]] = None
    context_after: Optional[Dict[str, Any]] = None
    updated_paths: List[str] = field(default_factory=list)
    removed_temp_keys: List[str] = field(default_factory=list)
    error: Optional[str] = None


@dataclass
class NewTaskGenerationPhase:
    """New task generation phase"""
    start_time: str
    end_time: Optional[str] = None
    status: ExecutionStatus = ExecutionStatus.STARTED
    tool_output: Any = None
    current_task_description: Optional[str] = None
    llm_call: Optional[LLMCall] = None
    generated_tasks: List[str] = field(default_factory=list)
    error: Optional[str] = None


@dataclass
class TaskExecutionRecord:
    """Complete record of a single task execution"""
    task_execution_id: str
    task_execution_counter: int
    task_description: str
    start_time: str
    end_time: Optional[str] = None
    status: ExecutionStatus = ExecutionStatus.STARTED
    error: Optional[str] = None
    
    engine_state_before: Optional[Dict[str, Any]] = None
    engine_state_after: Optional[Dict[str, Any]] = None
    
    phases: Dict[str, Union[SopResolutionPhase, TaskCreationPhase, TaskExecutionPhase, 
                           ContextUpdatePhase, NewTaskGenerationPhase]] = field(default_factory=dict)


@dataclass
class ExecutionSession:
    """Complete execution session with all task executions"""
    session_id: str
    start_time: str
    end_time: Optional[str] = None
    initial_task_description: Optional[str] = None
    final_status: ExecutionStatus = ExecutionStatus.STARTED
    
    engine_snapshots: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    task_executions: List[TaskExecutionRecord] = field(default_factory=list)


class ExecutionTracer:
    """Main tracer for capturing execution state and events"""
    
    def __init__(self, output_dir: str = "traces", enabled: bool = True):
        self.enabled = enabled
        self.output_dir = Path(output_dir)  # Always set output_dir regardless of enabled status
        
        if not enabled:
            return
            
        self.output_dir.mkdir(exist_ok=True)
        
        self.session: Optional[ExecutionSession] = None
        self.current_task_execution: Optional[TaskExecutionRecord] = None
        self.current_phase: Optional[str] = None
        self.tool_call_counter: int = 0
        self.current_session_file: Optional[str] = None  # Track current session file path
        
    def _current_time(self) -> str:
        """Get current timestamp in ISO format"""
        return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
    
    def _generate_id(self) -> str:
        """Generate unique ID"""
        return str(uuid.uuid4())
    
    def start_session(self, initial_task: str = None) -> str:
        """Start a new execution session"""
        if not self.enabled:
            return ""
            
        session_id = self._generate_id()
        self.session = ExecutionSession(
            session_id=session_id,
            start_time=self._current_time(),
            initial_task_description=initial_task
        )
        
        print(f"[TRACER] Started session: {session_id}")
        
        # Save initial session file for real-time monitoring
        self._save_session()
        
        return session_id
    
    def capture_engine_state(self, name: str, task_stack: List[str], context: Dict[str, Any], 
                           task_execution_counter: int) -> None:
        """Capture engine state snapshot"""
        if not self.enabled or not self.session:
            return
            
        self.session.engine_snapshots[name] = {
            "task_stack": task_stack.copy(),
            "context": json.loads(json.dumps(context)),  # Deep copy
            "task_execution_counter": task_execution_counter
        }
    
    def start_task_execution(self, task_description: str, engine_state: Dict[str, Any]) -> str:
        """Start a new task execution"""
        if not self.enabled or not self.session:
            return ""
            
        execution_id = self._generate_id()
        self.current_task_execution = TaskExecutionRecord(
            task_execution_id=execution_id,
            task_execution_counter=engine_state["task_execution_counter"],
            task_description=task_description,
            start_time=self._current_time(),
            engine_state_before=json.loads(json.dumps(engine_state))  # Deep copy
        )
        
        self.session.task_executions.append(self.current_task_execution)
        
        print(f"[TRACER] Started task execution: {task_description[:50]}...")
        
        # Save session file for real-time monitoring after task execution start
        self._save_session()
        
        return execution_id
    
    def start_phase(self, phase_name: str) -> None:
        """Start a new execution phase"""
        if not self.enabled or not self.current_task_execution:
            return
            
        self.current_phase = phase_name
        
        if phase_name == "sop_resolution":
            self.current_task_execution.phases[phase_name] = SopResolutionPhase(
                start_time=self._current_time()
            )
        elif phase_name == "task_creation":
            self.current_task_execution.phases[phase_name] = TaskCreationPhase(
                start_time=self._current_time()
            )
        elif phase_name == "task_execution":
            self.current_task_execution.phases[phase_name] = TaskExecutionPhase(
                start_time=self._current_time()
            )
        elif phase_name == "context_update":
            self.current_task_execution.phases[phase_name] = ContextUpdatePhase(
                start_time=self._current_time()
            )
        elif phase_name == "new_task_generation":
            self.current_task_execution.phases[phase_name] = NewTaskGenerationPhase(
                start_time=self._current_time()
            )
    
    def log_llm_call(self, prompt: str, response: str, step: str = None, 
                     model: str = None, token_usage: Dict[str, int] = None) -> str:
        """Log an LLM interaction"""
        if not self.enabled:
            return ""
            
        self.tool_call_counter += 1
        call_id = self._generate_id()
        
        llm_call = LLMCall(
            tool_call_id=call_id,
            step=step,
            prompt=prompt,
            response=response,
            start_time=self._current_time(),
            end_time=self._current_time(),
            model=model,
            token_usage=token_usage
        )
        
        # Store in appropriate phase
        if self.current_phase and self.current_task_execution:
            phase = self.current_task_execution.phases.get(self.current_phase)
            
            if isinstance(phase, SopResolutionPhase):
                phase.llm_validation_call = llm_call
            elif isinstance(phase, TaskCreationPhase):
                if step and "json_path" in step:
                    # This is for JSON path generation
                    field_name = step.replace("json_path_", "")
                    if field_name not in phase.json_path_generation:
                        phase.json_path_generation[field_name] = JsonPathGeneration(
                            field_name=field_name,
                            description=""
                        )
                    phase.json_path_generation[field_name].llm_calls.append(llm_call)
                else:
                    phase.output_path_generation = llm_call
            elif isinstance(phase, TaskExecutionPhase):
                phase.output_path_generation = llm_call
            elif isinstance(phase, NewTaskGenerationPhase):
                phase.llm_call = llm_call
        
        print(f"[TRACER] Logged LLM call: {step or 'unknown'}")
        return call_id
    
    def log_tool_call(self, tool_id: str, parameters: Dict[str, Any], output: Any, 
                     error: Exception = None) -> str:
        """Log a tool execution"""
        if not self.enabled:
            return ""
            
        call_id = self._generate_id()
        
        tool_call = ToolCall(
            tool_call_id=call_id,
            tool_id=tool_id,
            parameters=json.loads(json.dumps(parameters)),  # Deep copy
            output=output,
            start_time=self._current_time(),
            end_time=self._current_time(),
            status=ExecutionStatus.FAILED if error else ExecutionStatus.COMPLETED,
            error=str(error) if error else None
        )
        
        # Store in task execution phase
        if self.current_phase == "task_execution" and self.current_task_execution:
            phase = self.current_task_execution.phases.get("task_execution")
            if isinstance(phase, TaskExecutionPhase):
                phase.tool_execution = tool_call
        
        print(f"[TRACER] Logged tool call: {tool_id}")
        return call_id
    
    def end_phase(self, phase_data: Dict[str, Any] = None, error: Exception = None) -> None:
        """Complete the current phase"""
        if not self.enabled or not self.current_phase or not self.current_task_execution:
            return
            
        phase = self.current_task_execution.phases.get(self.current_phase)
        if phase:
            phase.end_time = self._current_time()
            phase.status = ExecutionStatus.FAILED if error else ExecutionStatus.COMPLETED
            if error:
                phase.error = str(error)
            
            # Update phase with additional data
            if phase_data:
                for key, value in phase_data.items():
                    if hasattr(phase, key):
                        setattr(phase, key, value)
        
        print(f"[TRACER] Ended phase: {self.current_phase}")
        
        # Save session file for real-time monitoring after phase completion
        self._save_session()
        
        self.current_phase = None
    
    def end_task_execution(self, engine_state: Dict[str, Any], status: ExecutionStatus, 
                          error: Exception = None) -> None:
        """Complete the current task execution"""
        if not self.enabled or not self.current_task_execution:
            return
            
        self.current_task_execution.end_time = self._current_time()
        self.current_task_execution.status = status
        if error:
            self.current_task_execution.error = str(error)
        
        self.current_task_execution.engine_state_after = json.loads(json.dumps(engine_state))
        
        print(f"[TRACER] Ended task execution: {status.value}")
        
        # Save session file for real-time monitoring after task execution completion
        self._save_session()
        
        self.current_task_execution = None
    
    def end_session(self, final_status: ExecutionStatus = ExecutionStatus.COMPLETED) -> str:
        """End the execution session and save to file"""
        if not self.enabled or not self.session:
            return ""
            
        self.session.end_time = self._current_time()
        self.session.final_status = final_status
        
        # Save to file
        filename = self._save_session()
        
        print(f"[TRACER] Ended session: {self.session.session_id}")
        print(f"[TRACER] Saved trace to: {filename}")
        
        session_id = self.session.session_id
        self.session = None
        self.current_session_file = None  # Reset session file path
        
        return filename
    
    def _save_session(self) -> str:
        """Save session data to JSON file"""
        if not self.session:
            return ""
        
        # Generate filename if not already set (first save)
        if not self.current_session_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"session_{timestamp}_{self.session.session_id[:8]}.json"
            self.current_session_file = str(self.output_dir / filename)
        
        # Convert to dict for JSON serialization
        session_dict = asdict(self.session)
        
        # Convert ExecutionStatus enums to strings recursively
        def convert_enums(obj):
            if isinstance(obj, dict):
                return {k: convert_enums(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_enums(item) for item in obj]
            elif isinstance(obj, ExecutionStatus):
                return obj.value
            else:
                return obj
        
        session_dict = convert_enums(session_dict)
        
        with open(self.current_session_file, 'w', encoding='utf-8') as f:
            json.dump(session_dict, f, ensure_ascii=False, indent=2)
        
        return self.current_session_file


class StateReconstructor:
    """Reconstruct engine state from trace files for replay"""
    
    def __init__(self, trace_file: str):
        self.trace_file = Path(trace_file)
        with open(self.trace_file, 'r', encoding='utf-8') as f:
            self.session_data = json.load(f)
    
    def get_engine_state_at_task(self, task_execution_counter: int) -> Dict[str, Any]:
        """Get engine state before specified task execution"""
        for task_exec in self.session_data["task_executions"]:
            if task_exec["task_execution_counter"] == task_execution_counter:
                return task_exec["engine_state_before"]
        
        # If not found, return initial state
        return self.session_data["engine_snapshots"].get("start", {})
    
    def get_task_executions_from(self, task_execution_counter: int) -> List[Dict[str, Any]]:
        """Get all task executions from specified counter onwards"""
        return [
            task_exec for task_exec in self.session_data["task_executions"]
            if task_exec["task_execution_counter"] >= task_execution_counter
        ]
    
    def print_session_summary(self) -> None:
        """Print a summary of the traced session"""
        print(f"Session ID: {self.session_data['session_id']}")
        print(f"Initial Task: {self.session_data.get('initial_task_description', 'N/A')}")
        print(f"Duration: {self.session_data['start_time']} -> {self.session_data.get('end_time', 'Running')}")
        print(f"Status: {self.session_data['final_status']}")
        print(f"Task Executions: {len(self.session_data['task_executions'])}")
        print()
        
        for i, task_exec in enumerate(self.session_data["task_executions"]):
            print(f"  {i+1}. Task #{task_exec['task_execution_counter']}: {task_exec['task_description'][:60]}...")
            print(f"     Status: {task_exec['status']}")
            if task_exec.get('error'):
                print(f"     Error: {task_exec['error']}")
