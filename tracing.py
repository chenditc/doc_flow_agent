#!/usr/bin/env python3
"""
Execution Tracing System for Doc Execute Engine
Provides observability and replay capabilities for task execution
"""

import json
import uuid
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Union, Callable, Generator, TYPE_CHECKING
from pathlib import Path
from enum import Enum
from contextlib import contextmanager

if TYPE_CHECKING:
    from doc_execute_engine import PendingTask


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
    tool_calls: Optional[List[Dict[str, Any]]] = None
    all_parameters: Optional[Dict[str, Any]] = None


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
class BatchInputFieldExtraction:
    """Container for batch input field extraction process using LLM tool schema"""
    input_descriptions: Dict[str, str]
    start_time: str
    end_time: Optional[str] = None
    status: ExecutionStatus = ExecutionStatus.STARTED
    
    # LLM calls in the batch extraction process
    context_analysis_call: Optional[LLMCall] = None
    batch_extraction_call: Optional[LLMCall] = None
    
    # Results
    candidate_fields: Dict[str, Any] = field(default_factory=dict)
    tool_schema: Optional[Dict[str, Any]] = None
    extracted_values: Dict[str, str] = field(default_factory=dict)  # field_name -> extracted_value
    generated_paths: Dict[str, str] = field(default_factory=dict)   # field_name -> json_path
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
    batch_input_field_extraction: Optional[BatchInputFieldExtraction] = None
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
    # Capture any nested LLM calls that happen during the tool execution
    llm_calls: List[LLMCall] = field(default_factory=list)
    
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
    output_path_generation: Optional[OutputPathGeneration] = None


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
    task_id: Optional[str] = None  # ID of the actual task being executed
    
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
        
        # Always initialize attributes to avoid AttributeError
        self.session: Optional[ExecutionSession] = None
        self.current_task_execution: Optional[TaskExecutionRecord] = None
        self._context = TracingContext()
        self.tool_call_counter: int = 0
        self.current_session_file: Optional[str] = None  # Track current session file path
        
        if not enabled:
            return
            
        self.output_dir.mkdir(exist_ok=True)
        
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
    
    def start_task_execution(self, pending_task: 'PendingTask', engine_state: Dict[str, Any]) -> str:
        """Start a new task execution"""
        if not self.enabled or not self.session:
            return ""
            
        execution_id = self._generate_id()
        self.current_task_execution = TaskExecutionRecord(
            task_execution_id=execution_id,
            task_execution_counter=engine_state["task_execution_counter"],
            task_description=pending_task.description,
            task_id=pending_task.task_id,
            start_time=self._current_time(),
            engine_state_before=json.loads(json.dumps(engine_state))  # Deep copy
        )
        
        self.session.task_executions.append(self.current_task_execution)
        
        print(f"[TRACER] Started task execution: {pending_task.description[:50]}...")
        print(f"[TRACER] Task ID: {pending_task.task_id}")
        
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
    
    def log_llm_call(self, prompt: str, response: str, model: str = None, 
                     token_usage: Dict[str, int] = None, tool_calls: List[Dict[str, Any]] = None,
                     all_parameters: Dict[str, Any] = None) -> str:
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
            token_usage=token_usage,
            tool_calls=tool_calls,
            all_parameters=all_parameters
        )
        
        # Use context-aware storage
        if self._context.llm_call_storage:
            self._context.llm_call_storage(llm_call)
        else:
            print(f"[TRACER] Warning: No storage context for LLM call in phase {self._context.current_phase}")
        
        print(f"[TRACER] Logged LLM call in {self._context.current_phase}.{self._context.current_sub_step or 'main'}")
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
    
    @contextmanager
    def trace_task_execution(self, pending_task: 'PendingTask', engine_state_provider: Optional[Callable[[], Dict[str, Any]]] = None) -> Generator['TaskExecutionContext', None, None]:
        """Context manager for tracing a full task execution lifecycle.

        Automatically starts a task execution on enter and ends it on exit.
        Status is inferred (COMPLETED/FAILED) unless explicitly overridden via context.set_status.

        Args:
            pending_task: The PendingTask object being executed (contains description and task_id)
            engine_state_provider: Callable to fetch the current engine state; called at enter and exit
        """
        if not self.enabled:
            yield TaskExecutionContext()
            return

        # Compute engine state before and start execution
        engine_state_before = engine_state_provider() if engine_state_provider else {}
        self.start_task_execution(pending_task, engine_state_before)

        ctx = TaskExecutionContext()
        exception: Optional[Exception] = None
        try:
            yield ctx
        except Exception as e:
            exception = e
            raise
        finally:
            # Determine status/error: prefer explicitly set status else infer from exception
            if ctx._status is not None:
                status = ctx._status
                err = ctx._error
            else:
                status = ExecutionStatus.FAILED if exception else ExecutionStatus.COMPLETED
                err = exception

            engine_state_after = engine_state_provider() if engine_state_provider else {}
            self.end_task_execution(engine_state_after, status, err)

    @contextmanager
    def trace_session(self, initial_task: Optional[str] = None, engine_state_provider: Optional[Callable[[], Dict[str, Any]]] = None) -> Generator['SessionContext', None, None]:
        """Context manager for tracing an execution session with automatic start/end and snapshots.

        On enter: starts a session and captures a "start" engine snapshot if provider is supplied.
        On normal exit: captures an "end" snapshot and ends the session (COMPLETED by default, override with ctx.set_status).
        On exception: captures an "error" snapshot and ends the session as FAILED, then re-raises.
        """
        if not self.enabled:
            yield SessionContext()
            return

        # Start session
        self.start_session(initial_task)

        # Optional start snapshot
        if engine_state_provider:
            try:
                state = engine_state_provider() or {}
                self.capture_engine_state(
                    "start",
                    state.get("task_stack", []),
                    state.get("context", {}),
                    state.get("task_execution_counter", 0),
                )
            except Exception as e:
                # Snapshot failures shouldn't crash; log and continue
                print(f"[TRACER] Warning: failed to capture start snapshot: {e}")

        ctx = SessionContext()
        exception: Optional[Exception] = None
        try:
            yield ctx
        except Exception as e:
            exception = e
            # Optional error snapshot
            if engine_state_provider:
                try:
                    state = engine_state_provider() or {}
                    self.capture_engine_state(
                        "error",
                        state.get("task_stack", []),
                        state.get("context", {}),
                        state.get("task_execution_counter", 0),
                    )
                except Exception as snap_err:
                    print(f"[TRACER] Warning: failed to capture error snapshot: {snap_err}")
            # End session as failed
            self.end_session(ExecutionStatus.FAILED)
            raise
        finally:
            if exception is None:
                # Optional end snapshot
                if engine_state_provider:
                    try:
                        state = engine_state_provider() or {}
                        self.capture_engine_state(
                            "end",
                            state.get("task_stack", []),
                            state.get("context", {}),
                            state.get("task_execution_counter", 0),
                        )
                    except Exception as e:
                        print(f"[TRACER] Warning: failed to capture end snapshot: {e}")
                # Respect explicit status, default to COMPLETED
                final_status = ctx._status or ExecutionStatus.COMPLETED
                self.end_session(final_status)

    @contextmanager
    def trace_phase(self, phase_name: str) -> Generator[None, None, None]:
        """Context manager for tracing execution phases with automatic error handling
        
        Usage:
            with tracer.trace_phase("task_execution"):
                # do work
                # if exception occurs, it will be automatically captured
                pass
        """
        if not self.enabled:
            yield
            return
            
        self.start_phase(phase_name)
        exception = None
        try:
            yield
        except Exception as e:
            exception = e
            raise  # Re-raise the exception
        finally:
            # Always end phase, passing exception if one occurred
            self.end_phase(error=exception)
    
    @contextmanager  
    def trace_phase_with_data(self, phase_name: str) -> Generator['PhaseContext', None, None]:
        """Context manager for tracing phases with data collection and automatic error handling
        
        Usage:
            with tracer.trace_phase_with_data("task_execution") as phase_ctx:
                # do work
                result = some_operation()
                phase_ctx.set_data({"result": result})
                # Data will be automatically passed to end_phase
        """
        if not self.enabled:
            yield PhaseContext()
            return
            
        self.start_phase(phase_name)
        phase_ctx = PhaseContext()
        exception = None
        try:
            yield phase_ctx
        except Exception as e:
            exception = e
            raise
        finally:
            # Always end phase, passing phase data and exception if one occurred
            self.end_phase(phase_ctx.data, error=exception)
    
    @contextmanager
    def trace_new_task_generation_step(self) -> Generator['NewTaskGenerationContext', None, None]:
        """Context manager for tracing new task generation steps
        
        Usage:
            with tracer.trace_new_task_generation_step() as step_ctx:
                # do task generation work
                new_tasks = some_task_generation()
                step_ctx.set_result(
                    generated_tasks=new_tasks,
                    tool_output=output,
                    task_description=description
                )
                # Results will be automatically passed to end_new_task_generation_step
        """
        if not self.enabled:
            yield NewTaskGenerationContext()
            return
        
        # Start new task generation step (inline logic from start_new_task_generation_step)
        if self._context.current_phase != "new_task_generation":
            yield NewTaskGenerationContext()
            return
            
        phase = self.current_task_execution.phases.get("new_task_generation")
        if not phase:
            yield NewTaskGenerationContext()
            return
            
        # Initialize the sub-step
        phase.task_generation = NewTaskGeneration(start_time=self._current_time())
        self._context.current_sub_step = "new_task_generation_step"
        self._context.llm_call_storage = lambda call: setattr(phase.task_generation, 'task_generation_call', call)
        
        step_ctx = NewTaskGenerationContext()
        exception = None
        try:
            yield step_ctx
        except Exception as e:
            exception = e
            raise
        finally:
            # End new task generation step (inline logic from end_new_task_generation_step)
            if phase and phase.task_generation:
                phase.task_generation.end_time = self._current_time()
                phase.task_generation.status = ExecutionStatus.FAILED if exception else ExecutionStatus.COMPLETED
                if exception:
                    phase.task_generation.error = str(exception)
                if step_ctx.generated_tasks:
                    phase.task_generation.generated_tasks = step_ctx.generated_tasks
                if step_ctx.tool_output is not None:
                    phase.task_generation.tool_output = step_ctx.tool_output
                if step_ctx.task_description:
                    phase.task_generation.current_task_description = step_ctx.task_description
            
            self._context.current_sub_step = None
            self._context.llm_call_storage = None
    
    @contextmanager
    def trace_document_selection_step(self) -> Generator['DocumentSelectionContext', None, None]:
        """Context manager for tracing document selection steps
        
        Usage:
            with tracer.trace_document_selection_step() as step_ctx:
                # do document selection work
                docs = find_candidate_documents()
                selected = select_document(docs)
                loaded = load_document(selected)
                step_ctx.set_result(
                    candidate_docs=docs,
                    selected_doc=selected,
                    loaded_doc=loaded
                )
        """
        if not self.enabled:
            yield DocumentSelectionContext()
            return
        
        # Start document selection step (inline logic from start_document_selection)
        if self._context.current_phase != "sop_resolution":
            yield DocumentSelectionContext()
            return
            
        phase = self.current_task_execution.phases.get("sop_resolution")
        if not phase:
            yield DocumentSelectionContext()
            return
            
        # Initialize the sub-step
        phase.document_selection = DocumentSelection(start_time=self._current_time())
        self._context.current_sub_step = "document_selection"
        self._context.llm_call_storage = lambda call: setattr(phase.document_selection, 'validation_call', call)
        
        step_ctx = DocumentSelectionContext()
        exception = None
        try:
            yield step_ctx
        except Exception as e:
            exception = e
            raise
        finally:
            # End document selection step (inline logic from end_document_selection)
            if phase and phase.document_selection:
                phase.document_selection.end_time = self._current_time()
                phase.document_selection.status = ExecutionStatus.FAILED if exception else ExecutionStatus.COMPLETED
                if exception:
                    phase.document_selection.error = str(exception)
                if step_ctx.candidate_docs:
                    phase.document_selection.candidate_documents = step_ctx.candidate_docs
                if step_ctx.selected_doc:
                    phase.document_selection.selected_doc_id = step_ctx.selected_doc
                if step_ctx.loaded_doc:
                    phase.document_selection.loaded_document = step_ctx.loaded_doc
            
            self._context.current_sub_step = None
            self._context.llm_call_storage = None
    
    @contextmanager
    def trace_input_field_extraction_step(self, field_name: str, description: str) -> Generator['InputFieldExtractionContext', None, None]:
        """Context manager for tracing input field extraction steps
        
        Usage:
            with tracer.trace_input_field_extraction_step('field_name', 'description') as step_ctx:
                # do field extraction work
                code = generate_extraction_code()
                value = extract_value(code)
                path = generate_path()
                step_ctx.set_result(
                    generated_code=code,
                    extracted_value=value,
                    generated_path=path
                )
        """
        if not self.enabled:
            yield InputFieldExtractionContext(field_name, description)
            return
        
        # Start input field extraction step (inline logic from start_input_field_extraction)
        if self._context.current_phase != "task_creation":
            yield InputFieldExtractionContext(field_name, description)
            return
            
        phase = self.current_task_execution.phases.get("task_creation")
        if not phase:
            yield InputFieldExtractionContext(field_name, description)
            return
            
        # Initialize the sub-step
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
        
        step_ctx = InputFieldExtractionContext(field_name, description)
        exception = None
        try:
            yield step_ctx
        except Exception as e:
            exception = e
            raise
        finally:
            # End input field extraction step (inline logic from end_input_field_extraction)
            if phase and extraction:
                extraction.end_time = self._current_time()
                extraction.status = ExecutionStatus.FAILED if exception else ExecutionStatus.COMPLETED
                if exception:
                    extraction.error = str(exception)
                if step_ctx.generated_code:
                    extraction.generated_extraction_code = step_ctx.generated_code
                if step_ctx.extracted_value is not None:
                    extraction.extracted_value = step_ctx.extracted_value
                if step_ctx.generated_path:
                    extraction.generated_path = step_ctx.generated_path
                if step_ctx.candidate_fields:
                    extraction.candidate_fields = step_ctx.candidate_fields
            
            self._context.current_sub_step = None
            self._context.current_field_name = None
            self._context.llm_call_storage = None
    
    @contextmanager
    def batch_extract_input_field(self, input_descriptions: Dict[str, str]) -> Generator['BatchInputFieldExtractionContext', None, None]:
        """Context manager for tracing batch input field extraction steps
        
        Usage:
            with tracer.batch_extract_input_field(input_descriptions) as batch_ctx:
                # do batch field extraction work
                candidates = analyze_context_candidates()
                schema = create_tool_schema()
                values = extract_all_fields_with_llm()
                paths = generate_paths()
                batch_ctx.set_result(
                    candidate_fields=candidates,
                    tool_schema=schema,
                    extracted_values=values,
                    generated_paths=paths
                )
        """
        if not self.enabled:
            yield BatchInputFieldExtractionContext(input_descriptions)
            return
        
        # Start batch input field extraction step
        if self._context.current_phase != "task_creation":
            yield BatchInputFieldExtractionContext(input_descriptions)
            return
            
        phase = self.current_task_execution.phases.get("task_creation")
        if not phase:
            yield BatchInputFieldExtractionContext(input_descriptions)
            return
            
        # Initialize the sub-step
        batch_extraction = BatchInputFieldExtraction(
            input_descriptions=input_descriptions,
            start_time=self._current_time()
        )
        phase.batch_input_field_extraction = batch_extraction
        self._context.current_sub_step = "batch_input_field_extraction"
        
        # Set up storage callback that routes to appropriate LLM call field
        def store_llm_call(call: LLMCall):
            if not batch_extraction.context_analysis_call:
                batch_extraction.context_analysis_call = call
            else:
                batch_extraction.batch_extraction_call = call
        
        self._context.llm_call_storage = store_llm_call
        
        step_ctx = BatchInputFieldExtractionContext(input_descriptions)
        exception = None
        try:
            yield step_ctx
        except Exception as e:
            exception = e
            raise
        finally:
            # End batch input field extraction step
            if phase and batch_extraction:
                batch_extraction.end_time = self._current_time()
                batch_extraction.status = ExecutionStatus.FAILED if exception else ExecutionStatus.COMPLETED
                if exception:
                    batch_extraction.error = str(exception)
                if step_ctx.candidate_fields:
                    batch_extraction.candidate_fields = step_ctx.candidate_fields
                if step_ctx.tool_schema:
                    batch_extraction.tool_schema = step_ctx.tool_schema
                if step_ctx.extracted_values:
                    batch_extraction.extracted_values = step_ctx.extracted_values
                if step_ctx.generated_paths:
                    batch_extraction.generated_paths = step_ctx.generated_paths
            
            self._context.current_sub_step = None
            self._context.llm_call_storage = None
    
    @contextmanager
    def trace_output_path_generation_step(self) -> Generator['OutputPathGenerationContext', None, None]:
        """Context manager for tracing output path generation steps
        
        Usage:
            with tracer.trace_output_path_generation_step() as step_ctx:
                # do path generation work
                path = generate_output_path()
                prefixed = add_prefix(path)
                step_ctx.set_result(
                    generated_path=path,
                    prefixed_path=prefixed
                )
        """
        if not self.enabled:
            yield OutputPathGenerationContext()
            return
        
        # Start output path generation step (inline logic from start_output_path_generation)
        current_time = self._current_time()
        output_gen = None
        
        assert(self._context.current_phase == "context_update")

        phase = self.current_task_execution.phases.get("context_update")
        assert(phase is not None)

        phase.output_path_generation = OutputPathGeneration(start_time=current_time)
        output_gen = phase.output_path_generation
        self._context.current_sub_step = "output_path_generation"
        self._context.llm_call_storage = lambda call: setattr(phase.output_path_generation, 'path_generation_call', call)

        assert(output_gen is not None)
        
        step_ctx = OutputPathGenerationContext()
        exception = None
        try:
            yield step_ctx
        except Exception as e:
            exception = e
            raise
        finally:
            # End output path generation step (inline logic from end_output_path_generation)
            if output_gen:
                output_gen.end_time = self._current_time()
                output_gen.status = ExecutionStatus.FAILED if exception else ExecutionStatus.COMPLETED
                if exception:
                    output_gen.error = str(exception)
                if step_ctx.generated_path:
                    output_gen.generated_path = step_ctx.generated_path
                if step_ctx.prefixed_path:
                    output_gen.prefixed_path = step_ctx.prefixed_path
            
            self._context.current_sub_step = None
            self._context.llm_call_storage = None

    @contextmanager
    def trace_tool_execution_step(self) -> Generator['ToolExecutionContext', None, None]:
        """Context manager to capture LLM calls that occur during tool execution.

        Use this within the task_execution phase around the actual tool invocation so that
        any LLM calls made by the tool (or nested tools) are recorded under the current
        TaskExecutionPhase.

        Usage:
            with tracer.trace_tool_execution_step():
                output = await tool.execute(params)
        """
        if not self.enabled:
            yield ToolExecutionContext()
            return

        # Only active during task_execution phase
        if self._context.current_phase != "task_execution":
            yield ToolExecutionContext()
            return

        phase = self.current_task_execution.phases.get("task_execution")
        if not isinstance(phase, TaskExecutionPhase):
            yield ToolExecutionContext()
            return

        # Set up storage to append any LLM calls to the phase.llm_calls list
        self._context.current_sub_step = "tool_execution"
        self._context.llm_call_storage = lambda call: phase.llm_calls.append(call)

        step_ctx = ToolExecutionContext()
        try:
            yield step_ctx
        finally:
            self._context.current_sub_step = None
            self._context.llm_call_storage = None
    
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


class PhaseContext:
    """Helper class to collect phase data for context manager"""
    def __init__(self):
        self.data = {}
    
    def set_data(self, data: Dict[str, Any]):
        """Set the phase data to be passed to end_phase"""
        self.data = data
    
    def update_data(self, data: Dict[str, Any]):
        """Update the phase data"""
        self.data.update(data)


class NewTaskGenerationContext:
    """Helper class to collect new task generation step data for context manager"""
    def __init__(self):
        self.generated_tasks: Optional[List[str]] = None
        self.tool_output: Any = None
        self.task_description: Optional[str] = None
    
    def set_result(self, generated_tasks: List[str] = None, tool_output: Any = None, 
                   task_description: str = None):
        """Set the task generation results"""
        if generated_tasks is not None:
            self.generated_tasks = generated_tasks
        if tool_output is not None:
            self.tool_output = tool_output
        if task_description is not None:
            self.task_description = task_description


class DocumentSelectionContext:
    """Helper class to collect document selection step data for context manager"""
    def __init__(self):
        self.candidate_docs: Optional[List[str]] = None
        self.selected_doc: Optional[str] = None
        self.loaded_doc: Optional[Dict[str, Any]] = None
    
    def set_result(self, candidate_docs: List[str] = None, selected_doc: str = None, 
                   loaded_doc: Dict[str, Any] = None):
        """Set the document selection results"""
        if candidate_docs is not None:
            self.candidate_docs = candidate_docs
        if selected_doc is not None:
            self.selected_doc = selected_doc
        if loaded_doc is not None:
            self.loaded_doc = loaded_doc


class InputFieldExtractionContext:
    """Helper class to collect input field extraction step data for context manager"""
    def __init__(self, field_name: str, description: str):
        self.field_name = field_name
        self.description = description
        self.generated_code: Optional[str] = None
        self.extracted_value: Any = None
        self.generated_path: Optional[str] = None
        self.candidate_fields: Optional[Dict[str, Any]] = None
    
    def set_result(self, generated_code: str = None, extracted_value: Any = None,
                   generated_path: str = None, candidate_fields: Dict[str, Any] = None):
        """Set the input field extraction results"""
        if generated_code is not None:
            self.generated_code = generated_code
        if extracted_value is not None:
            self.extracted_value = extracted_value
        if generated_path is not None:
            self.generated_path = generated_path
        if candidate_fields is not None:
            self.candidate_fields = candidate_fields


class BatchInputFieldExtractionContext:
    """Helper class to collect batch input field extraction step data for context manager"""
    def __init__(self, input_descriptions: Dict[str, str]):
        self.input_descriptions = input_descriptions
        self.candidate_fields: Optional[Dict[str, Any]] = None
        self.tool_schema: Optional[Dict[str, Any]] = None
        self.extracted_values: Optional[Dict[str, str]] = None
        self.generated_paths: Optional[Dict[str, str]] = None
    
    def set_result(self, candidate_fields: Dict[str, Any] = None, tool_schema: Dict[str, Any] = None,
                   extracted_values: Dict[str, str] = None, generated_paths: Dict[str, str] = None):
        """Set the batch input field extraction results"""
        if candidate_fields is not None:
            self.candidate_fields = candidate_fields
        if tool_schema is not None:
            self.tool_schema = tool_schema
        if extracted_values is not None:
            self.extracted_values = extracted_values
        if generated_paths is not None:
            self.generated_paths = generated_paths


class OutputPathGenerationContext:
    """Helper class to collect output path generation step data for context manager"""
    def __init__(self):
        self.generated_path: Optional[str] = None
        self.prefixed_path: Optional[str] = None
    
    def set_result(self, generated_path: str = None, prefixed_path: str = None):
        """Set the output path generation results"""
        if generated_path is not None:
            self.generated_path = generated_path
        if prefixed_path is not None:
            self.prefixed_path = prefixed_path


class ToolExecutionContext:
    """Helper context for tool execution tracing.

    Currently a placeholder in case we want to attach extra metadata later.
    """
    def __init__(self):
        pass


class TaskExecutionContext:
    """Helper to control the final status of a task within trace_task_execution.

    If not set explicitly, status is inferred based on exception presence.
    """
    def __init__(self):
        self._status: Optional[ExecutionStatus] = None
        self._error: Optional[Exception] = None

    def set_status(self, status: ExecutionStatus, error: Exception = None):
        self._status = status
        self._error = error


class SessionContext:
    """Helper to choose final session status within trace_session.

    If not set explicitly, status defaults to COMPLETED unless an exception occurs.
    """
    def __init__(self):
        self._status: Optional[ExecutionStatus] = None

    def set_status(self, status: ExecutionStatus):
        self._status = status


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
