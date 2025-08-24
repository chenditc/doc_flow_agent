/**
 * Core trace data types for Doc Flow Trace Viewer
 */

export interface TraceSession {
  session_id: string;
  start_time: string;
  end_time: string | null;
  initial_task_description: string;
  final_status: 'running' | 'completed' | 'error' | 'cancelled';
  engine_snapshots: {
    start: EngineState;
    end?: EngineState;
  };
  task_executions: TaskExecution[];
}

export interface EngineState {
  task_stack: any[];
  context: Record<string, any>;
  task_execution_counter: number;
}

export interface TaskExecution {
  task_execution_id: string;
  task_execution_counter: number;
  task_description: string;
  start_time: string;
  end_time: string | null;
  status: 'running' | 'completed' | 'error' | 'cancelled';
  error: string | null;
  engine_state_before: EngineState;
  engine_state_after?: EngineState;
  phases: TaskPhases;
}

export interface TaskPhases {
  sop_resolution?: SOPResolutionPhase;
  task_creation?: TaskCreationPhase;
  task_execution?: TaskExecutionPhase;
  context_update?: ContextUpdatePhase;
  new_task_generation?: NewTaskGenerationPhase;
}

// SOP Resolution Phase (Updated for new tracing structure)
export interface SOPResolutionPhase {
  start_time: string;
  end_time: string | null;
  status: PhaseStatus;
  input?: {
    description: string;
  } | null;
  document_selection?: DocumentSelection | null;
  error: string | null;
}

export interface DocumentSelection {
  start_time: string;
  end_time: string | null;
  status: PhaseStatus;
  validation_call?: LLMCall | null;
  candidate_documents: string[];
  selected_doc_id: string | null;
  loaded_document?: any | null;
  error: string | null;
}

export interface SOPDocument {
  doc_id: string;
  description: string;
  aliases: string[];
  tool: {
    tool_id: string;
  };
  input_json_path: Record<string, any>;
  output_json_path: string;
  body: string;
  parameters: Record<string, any>;
  input_description: Record<string, string>;
  output_description: string;
}

// Task Creation Phase (Updated for new tracing structure)
export interface TaskCreationPhase {
  start_time: string;
  end_time: string | null;
  status: PhaseStatus;
  sop_document?: SOPDocument | null;
  input_field_extractions: Record<string, InputFieldExtraction>;
  output_path_generation?: OutputPathGeneration | null;
  created_task?: Task | null;
  error: string | null;
}

export interface InputFieldExtraction {
  field_name: string;
  description: string;
  start_time: string;
  end_time: string | null;
  status: PhaseStatus;
  context_analysis_call?: LLMCall | null;
  extraction_code_generation_call?: LLMCall | null;
  candidate_fields: Record<string, any>;
  generated_extraction_code?: string | null;
  extracted_value: any;
  generated_path?: string | null;
  error: string | null;
}

export interface OutputPathGeneration {
  start_time: string;
  end_time: string | null;
  status: PhaseStatus;
  path_generation_call?: LLMCall | null;
  generated_path?: string | null;
  prefixed_path?: string | null;
  error: string | null;
}

// Legacy JsonPathGeneration interface (kept for backward compatibility)
export interface JsonPathGeneration {
  field_name: string;
  description: string;
  llm_calls: LLMCall[];
  generated_path: string | null;
  extracted_value: any;
  error: string | null;
}

export interface Task {
  task_id: string;
  description: string;
  sop_doc_id: string;
  tool: {
    tool_id: string;
    parameters?: Record<string, any>;
  };
  input_json_path: Record<string, string>;
  output_json_path: string;
  output_description: string;
}

// Task Execution Phase (Updated for new tracing structure)
export interface TaskExecutionPhase {
  start_time: string;
  end_time: string | null;
  status: PhaseStatus;
  task?: Task | null;
  input_resolution?: {
    resolved_inputs: Record<string, any>;
  } | null;
  tool_execution?: ToolExecution | null;
  output_path_generation?: OutputPathGeneration | null;
  generated_path?: string | null;
  prefixed_path?: string | null;
  error: string | null;
}

export interface ToolExecution {
  tool_call_id: string;
  tool_id: string;
  parameters: Record<string, any>;
  output: string;
  start_time: string;
  end_time: string;
  status: PhaseStatus;
  error: string | null;
}

// Context Update Phase
export interface ContextUpdatePhase {
  start_time: string;
  end_time: string | null;
  status: PhaseStatus;
  context_before: Record<string, any>;
  context_after: Record<string, any>;
  updated_paths: string[];
  removed_temp_keys: string[];
  error: string | null;
}

// New Task Generation Phase (Updated for new tracing structure)
export interface NewTaskGenerationPhase {
  start_time: string;
  end_time: string | null;
  status: PhaseStatus;
  task_generation?: NewTaskGeneration | null;
  error: string | null;
}

export interface NewTaskGeneration {
  start_time: string;
  end_time: string | null;
  status: PhaseStatus;
  task_generation_call?: LLMCall | null;
  tool_output: any;
  current_task_description?: string | null;
  generated_tasks: string[];
  error: string | null;
}

// Common Types (Updated for new tracing structure)
export interface LLMCall {
  tool_call_id: string;
  prompt: string;
  response: string;
  start_time: string;
  end_time: string;
  model?: string | null;
  token_usage?: any | null;
}

export type PhaseStatus = 'started' | 'completed' | 'failed' | 'interrupted' | 'retrying';

// Timeline visualization types
export interface TimelineItem {
  id: string;
  title: string;
  description?: string;
  start_time: string;
  end_time: string | null;
  status: PhaseStatus;
  type: 'task' | 'phase' | 'llm_call' | 'tool_execution';
  data: any;
  children?: TimelineItem[];
}

// UI State Types
export interface TaskDetailsModalData {
  taskExecution: TaskExecution;
  isOpen: boolean;
}

export interface SOPResolutionViewerData {
  phase: SOPResolutionPhase;
  isExpanded: boolean;
}

export interface LLMCallData {
  call: LLMCall;
  isExpanded: boolean;
}
