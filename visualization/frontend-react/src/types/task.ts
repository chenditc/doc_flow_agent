/**
 * Task execution related types for Doc Flow Trace Viewer
 */

export interface TaskSummary {
  task_id: string;
  description: string;
  status: TaskStatus;
  start_time: string;
  end_time: string | null;
  duration: number | null;
  error: string | null;
}

export interface TaskPhasesSummary {
  sop_resolution?: PhaseSummary;
  task_creation?: PhaseSummary;
  task_execution?: PhaseSummary;
  context_update?: PhaseSummary;
  new_task_generation?: PhaseSummary;
}

export interface PhaseSummary {
  name: string;
  status: TaskStatus;
  start_time: string;
  end_time: string | null;
  duration: number | null;
  error: string | null;
  details?: any;
}

export interface TaskOutput {
  type: 'tool_output' | 'context_update' | 'error';
  content: any;
  format: 'json' | 'text' | 'html';
  timestamp: string;
}

export type TaskStatus = 'running' | 'completed' | 'error' | 'cancelled' | 'pending';

// Task filtering and sorting
export interface TaskFilter {
  status?: TaskStatus[];
  dateRange?: {
    start: string;
    end: string;
  };
  searchText?: string;
  hasErrors?: boolean;
}

export interface TaskSortOption {
  field: 'start_time' | 'end_time' | 'duration' | 'status' | 'description';
  direction: 'asc' | 'desc';
}

// Task execution statistics
export interface TaskStatistics {
  total_tasks: number;
  completed_tasks: number;
  error_tasks: number;
  running_tasks: number;
  average_duration: number;
  total_duration: number;
  llm_calls_count: number;
  tool_executions_count: number;
}
