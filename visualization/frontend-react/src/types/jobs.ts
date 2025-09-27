/**
 * Job-related types for orchestrator service integration
 */

export interface Job {
  job_id: string;
  task_description: string;
  status: 'QUEUED' | 'STARTING' | 'RUNNING' | 'COMPLETED' | 'FAILED' | 'CANCELLED';
  created_at: string;
  started_at?: string | null;
  finished_at?: string | null;
  trace_files: string[];
  max_tasks?: number;
  error?: Record<string, any> | null;
}

export interface SubmitJobRequest {
  task_description: string;
  max_tasks?: number;
}

export interface SubmitJobResponse {
  job_id: string;
  status: string;
}

export interface CancelJobResponse {
  job_id: string;
  status: string;
  cancelled: boolean;
}

export interface JobLogsResponse {
  job_id: string;
  logs: string;
}

export interface JobContextResponse {
  job_id: string;
  context: any;
}

export type JobStatus = Job['status'];

export interface JobListFilters {
  status?: JobStatus;
  limit?: number;
}