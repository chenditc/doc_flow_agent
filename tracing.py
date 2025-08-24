#!/usr/bin/env python3
"""
Execution Tracing System for Doc Execute Engine
Provides observability and replay capabilities for task execution
"""

import json
import uuid
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Union, Callable
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
class InputFieldExtraction:
    """Container for input field value extraction process"""
    field_name: str
    description: str
    start_time: str
    end_time: Optional[str] = None
    status: ExecutionStatus = ExecutionStatus.STARTED
    
    # LLM calls in the extraction process
    context_analysis_call: Optional[LLMCall] = None
    extraction_code_generation_call: Optional[LLMCall] = None
    
    # Results
    candidate_fields: Dict[str, Any] = field(default_factory=dict)
    generated_extraction_code: Optional[str] = None
    extracted_value: Any = None
    generated_path: Optional[str] = None
    error: Optional[str] = None


@dataclass
class OutputPathGeneration:
    """Container for output path generation process"""
    start_time: str
    end_time: Optional[str] = None
    status: ExecutionStatus = ExecutionStatus.STARTED
    
    # LLM call for path generation
    path_generation_call: Optional[LLMCall] = None
    
    # Results
    generated_path: Optional[str] = None
    prefixed_path: Optional[str] = None
    error: Optional[str] = None


@dataclass
class DocumentSelection:
    """Container for SOP document selection process"""
    start_time: str
    end_time: Optional[str] = None
    status: ExecutionStatus = ExecutionStatus.STARTED
    
    # LLM call for validation
    validation_call: Optional[LLMCall] = None
    
    # Results
    candidate_documents: List[str] = field(default_factory=list)
    selected_doc_id: Optional[str] = None
    loaded_document: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


@dataclass
class NewTaskGeneration:
    """Container for new task generation process"""
    start_time: str
    end_time: Optional[str] = None
    status: ExecutionStatus = ExecutionStatus.STARTED
    
    # LLM call for task generation
    task_generation_call: Optional[LLMCall] = None
    
    # Results
    tool_output: Any = None
    current_task_description: Optional[str] = None
    generated_tasks: List[str] = field(default_factory=list)
    error: Optional[str] = None


@dataclass
class SopResolutionPhase:
    """SOP document resolution phase with structured sub-steps"""
    start_time: str
    end_time: Optional[str] = None
    status: ExecutionStatus = ExecutionStatus.STARTED
    input: Optional[Dict[str, Any]] = None
    
    # Sub-step containers
    document_selection: Optional[DocumentSelection] = None
    
    error: Optional[str] = None


@dataclass
class JsonPathGeneration:
    """JSON path generation for a single input field"""
    field_name: str
    description: str
    llm_calls: List[LLMCall] = field(default_factory=list)
    generated_path: Optional[str] = None
    extracted_value: Dict[str, str] = None # Key is input field name, value is extracted value
    error: Optional[str] = None


@dataclass
class TaskCreationPhase:
    """Task creation phase with structured sub-steps"""
    start_time: str
    end_time: Optional[str] = None
    status: ExecutionStatus = ExecutionStatus.STARTED
    sop_document: Optional[Dict[str, Any]] = None
    
    # Sub-step containers
    input_field_extractions: Dict[str, InputFieldExtraction] = field(default_factory=dict)
    output_path_generation: Optional[OutputPathGeneration] = None
    
    created_task: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


@dataclass
class TaskExecutionPhase:
    """Task execution phase with structured sub-steps"""
    start_time: str
    end_time: Optional[str] = None
    status: ExecutionStatus = ExecutionStatus.STARTED
    task: Optional[Dict[str, Any]] = None
    input_resolution: Optional[Dict[str, Any]] = None
    tool_execution: Optional[ToolCall] = None
    
    # Sub-step containers
    output_path_generation: Optional[OutputPathGeneration] = None
    
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
    """New task generation phase with structured sub-steps"""
    start_time: str
    end_time: Optional[str] = None
    status: ExecutionStatus = ExecutionStatus.STARTED
    
    # Sub-step containers
    task_generation: Optional[NewTaskGeneration] = None
    
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


@dataclass
class TracingContext:
    """Internal context for tracking current tracing state"""
    current_phase: Optional[str] = None
    current_sub_step: Optional[str] = None
    current_field_name: Optional[str] = None  # For input field extraction
    
    # Callbacks to store LLM calls
    llm_call_storage: Optional[Callable[[LLMCall], None]] = None


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
        
        # New: Internal tracing context
        self._context = TracingContext()
        
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
            
        self._context.current_phase = phase_name
        self._context.current_sub_step = None
        self._context.current_field_name = None
        self._context.llm_call_storage = None
        
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
    
    # New: Sub-step methods for structured tracing
    def start_document_selection(self) -> None:
        """Start SOP document selection sub-step"""
        if not self.enabled or self._context.current_phase != "sop_resolution":
            return
        
        phase = self.current_task_execution.phases.get("sop_resolution")
        if phase:
            phase.document_selection = DocumentSelection(start_time=self._current_time())
            self._context.current_sub_step = "document_selection"
            # Set up storage callback
            self._context.llm_call_storage = lambda call: setattr(phase.document_selection, 'validation_call', call)
    
    def start_input_field_extraction(self, field_name: str, description: str) -> None:
        """Start input field value extraction sub-step"""
        if not self.enabled or self._context.current_phase != "task_creation":
            return
        
        phase = self.current_task_execution.phases.get("task_creation")
        if phase:
            extraction = InputFieldExtraction(
                field_name=field_name,
                description=description,
                start_time=self._current_time()
            )
            phase.input_field_extractions[field_name] = extraction
            self._context.current_sub_step = "input_field_extraction"
            self._context.current_field_name = field_name
            
            # Set up storage callback that routes to appropriate LLM call field
            def store_llm_call(call: LLMCall):
                if not extraction.context_analysis_call:
                    extraction.context_analysis_call = call
                else:
                    extraction.extraction_code_generation_call = call
            
            self._context.llm_call_storage = store_llm_call
    
    def start_output_path_generation(self) -> None:
        """Start output path generation sub-step"""
        if not self.enabled:
            return
        
        current_time = self._current_time()
        
        if self._context.current_phase == "task_creation":
            phase = self.current_task_execution.phases.get("task_creation")
            if phase:
                phase.output_path_generation = OutputPathGeneration(start_time=current_time)
                self._context.current_sub_step = "output_path_generation"
                self._context.llm_call_storage = lambda call: setattr(phase.output_path_generation, 'path_generation_call', call)
        
        elif self._context.current_phase == "task_execution":
            phase = self.current_task_execution.phases.get("task_execution")
            if phase:
                phase.output_path_generation = OutputPathGeneration(start_time=current_time)
                self._context.current_sub_step = "output_path_generation"
                self._context.llm_call_storage = lambda call: setattr(phase.output_path_generation, 'path_generation_call', call)
    
    def start_new_task_generation_step(self) -> None:
        """Start new task generation sub-step"""
        if not self.enabled or self._context.current_phase != "new_task_generation":
            return
        
        phase = self.current_task_execution.phases.get("new_task_generation")
        if phase:
            phase.task_generation = NewTaskGeneration(start_time=self._current_time())
            self._context.current_sub_step = "new_task_generation_step"
            self._context.llm_call_storage = lambda call: setattr(phase.task_generation, 'task_generation_call', call)
    
    def log_llm_call(self, prompt: str, response: str, model: str = None, 
                     token_usage: Dict[str, int] = None) -> str:
        """Log an LLM interaction - simplified interface"""
        if not self.enabled:
            return ""
        
        call_id = self._generate_id()
        llm_call = LLMCall(
            tool_call_id=call_id,
            prompt=prompt,
            response=response,
            start_time=self._current_time(),
            end_time=self._current_time(),
            model=model,
            token_usage=token_usage
        )
        
        # Use context-aware storage
        if self._context.llm_call_storage:
            self._context.llm_call_storage(llm_call)
        else:
            print(f"[TRACER] Warning: No storage context for LLM call in phase {self._context.current_phase}")
        
        print(f"[TRACER] Logged LLM call in {self._context.current_phase}.{self._context.current_sub_step or 'main'}")
        return call_id
    
    # Sub-step completion methods
    def end_document_selection(self, candidate_docs: List[str] = None, selected_doc: str = None, 
                             loaded_doc: Dict[str, Any] = None, error: Exception = None) -> None:
        """End document selection sub-step"""
        if not self.enabled or self._context.current_sub_step != "document_selection":
            return
        
        phase = self.current_task_execution.phases.get("sop_resolution")
        if phase and phase.document_selection:
            phase.document_selection.end_time = self._current_time()
            phase.document_selection.status = ExecutionStatus.FAILED if error else ExecutionStatus.COMPLETED
            if error:
                phase.document_selection.error = str(error)
            if candidate_docs:
                phase.document_selection.candidate_documents = candidate_docs
            if selected_doc:
                phase.document_selection.selected_doc_id = selected_doc
            if loaded_doc:
                phase.document_selection.loaded_document = loaded_doc
        
        self._context.current_sub_step = None
        self._context.llm_call_storage = None
    
    def end_input_field_extraction(self, generated_code: str = None, extracted_value: Any = None,
                                 generated_path: str = None, candidate_fields: Dict[str, Any] = None,
                                 error: Exception = None) -> None:
        """End input field extraction sub-step"""
        if not self.enabled or self._context.current_sub_step != "input_field_extraction":
            return
        
        phase = self.current_task_execution.phases.get("task_creation")
        if phase and self._context.current_field_name:
            extraction = phase.input_field_extractions.get(self._context.current_field_name)
            if extraction:
                extraction.end_time = self._current_time()
                extraction.status = ExecutionStatus.FAILED if error else ExecutionStatus.COMPLETED
                if error:
                    extraction.error = str(error)
                if generated_code:
                    extraction.generated_extraction_code = generated_code
                if extracted_value is not None:
                    extraction.extracted_value = extracted_value
                if generated_path:
                    extraction.generated_path = generated_path
                if candidate_fields:
                    extraction.candidate_fields = candidate_fields
        
        self._context.current_sub_step = None
        self._context.current_field_name = None
        self._context.llm_call_storage = None
    
    def end_output_path_generation(self, generated_path: str = None, prefixed_path: str = None,
                                 error: Exception = None) -> None:
        """End output path generation sub-step"""
        if not self.enabled or self._context.current_sub_step != "output_path_generation":
            return
        
        # Find the appropriate phase
        output_gen = None
        if self._context.current_phase == "task_creation":
            phase = self.current_task_execution.phases.get("task_creation")
            if phase:
                output_gen = phase.output_path_generation
        elif self._context.current_phase == "task_execution":
            phase = self.current_task_execution.phases.get("task_execution")
            if phase:
                output_gen = phase.output_path_generation
        
        if output_gen:
            output_gen.end_time = self._current_time()
            output_gen.status = ExecutionStatus.FAILED if error else ExecutionStatus.COMPLETED
            if error:
                output_gen.error = str(error)
            if generated_path:
                output_gen.generated_path = generated_path
            if prefixed_path:
                output_gen.prefixed_path = prefixed_path
        
        self._context.current_sub_step = None
        self._context.llm_call_storage = None
    
    def end_new_task_generation_step(self, generated_tasks: List[str] = None, tool_output: Any = None,
                              task_description: str = None, error: Exception = None) -> None:
        """End new task generation sub-step"""
        if not self.enabled or self._context.current_sub_step != "new_task_generation_step":
            return
        
        phase = self.current_task_execution.phases.get("new_task_generation")
        if phase and phase.task_generation:
            phase.task_generation.end_time = self._current_time()
            phase.task_generation.status = ExecutionStatus.FAILED if error else ExecutionStatus.COMPLETED
            if error:
                phase.task_generation.error = str(error)
            if generated_tasks:
                phase.task_generation.generated_tasks = generated_tasks
            if tool_output is not None:
                phase.task_generation.tool_output = tool_output
            if task_description:
                phase.task_generation.current_task_description = task_description
        
        self._context.current_sub_step = None
        self._context.llm_call_storage = None
    
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
        if self._context.current_phase == "task_execution" and self.current_task_execution:
            phase = self.current_task_execution.phases.get("task_execution")
            if isinstance(phase, TaskExecutionPhase):
                phase.tool_execution = tool_call
        
        print(f"[TRACER] Logged tool call: {tool_id}")
        return call_id
    
    def end_phase(self, phase_data: Dict[str, Any] = None, error: Exception = None) -> None:
        """Complete the current phase"""
        if not self.enabled or not self._context.current_phase or not self.current_task_execution:
            return
            
        phase = self.current_task_execution.phases.get(self._context.current_phase)
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
        
        print(f"[TRACER] Ended phase: {self._context.current_phase}")
        
        # Save session file for real-time monitoring after phase completion
        self._save_session()
        
        self._context.current_phase = None
    
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
