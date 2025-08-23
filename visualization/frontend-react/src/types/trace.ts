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

// SOP Resolution Phase
export interface SOPResolutionPhase {
  start_time: string;
  end_time: string | null;
  status: PhaseStatus;
  input: {
    description: string;
  };
  candidate_documents: string[];
  llm_validation_call?: LLMCall;
  selected_doc_id: string | null;
  loaded_sop_document?: SOPDocument;
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

// Task Creation Phase
export interface TaskCreationPhase {
  start_time: string;
  end_time: string | null;
  status: PhaseStatus;
  sop_document: SOPDocument;
  json_path_generation: Record<string, JsonPathGeneration>;
  output_path_generation?: any;
  created_task: Task;
  error: string | null;
}

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
  };
  input_json_path: Record<string, string>;
  output_json_path: string;
  output_description: string;
}

// Task Execution Phase
export interface TaskExecutionPhase {
  start_time: string;
  end_time: string | null;
  status: PhaseStatus;
  task: Task;
  input_resolution: {
    resolved_inputs: Record<string, any>;
  };
  tool_execution: ToolExecution;
  output_path_generation?: LLMCall;
  generated_path?: string;
  prefixed_path?: string;
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

// New Task Generation Phase
export interface NewTaskGenerationPhase {
  start_time: string;
  end_time: string | null;
  status: PhaseStatus;
  tool_output: string;
  current_task_description: string;
  llm_call: LLMCall;
  generated_tasks: string[];
  error: string | null;
}

// Common Types
export interface LLMCall {
  tool_call_id: string;
  step: string;
  prompt: string;
  response: string;
  start_time: string;
  end_time: string;
  model: string;
  token_usage: any;
}

export type PhaseStatus = 'running' | 'completed' | 'error' | 'cancelled';

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
