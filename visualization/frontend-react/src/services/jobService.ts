/**
 * Job-specific API service
 * Handles all orchestrator service job operations
 */

import type { 
  Job, 
  SubmitJobRequest, 
  SubmitJobResponse, 
  CancelJobResponse, 
  JobLogsResponse, 
  JobContextResponse,
  JobListFilters 
} from '../types';
import { ApiClient } from './api';

export class JobService {
  private apiClient: ApiClient;

  constructor(apiClient: ApiClient) {
    this.apiClient = apiClient;
  }

  /**
   * Submit a new job for execution
   * @param data - Job submission data
   * @returns Promise<SubmitJobResponse> The job submission result
   */
  async submitJob(data: SubmitJobRequest): Promise<SubmitJobResponse> {
    if (!data.task_description?.trim()) {
      throw new Error('Task description is required');
    }

    return this.apiClient.post<SubmitJobResponse>('/jobs', data);
  }

  /**
   * Fetch list of jobs with optional filtering
   * @param filters - Optional filters for status and limit
   * @returns Promise<Job[]> List of jobs
   */
  async listJobs(filters: JobListFilters = {}): Promise<Job[]> {
    const params = new URLSearchParams();
    
    if (filters.status) {
      params.append('status', filters.status);
    }
    
    if (filters.limit) {
      params.append('limit', filters.limit.toString());
    }

    const queryString = params.toString();
    const url = queryString ? `/jobs?${queryString}` : '/jobs';
    
    return this.apiClient.get<Job[]>(url);
  }

  /**
   * Fetch a specific job by ID
   * @param jobId - The job ID to fetch
   * @returns Promise<Job> The job data
   */
  async getJob(jobId: string): Promise<Job> {
    if (!jobId?.trim()) {
      throw new Error('Job ID is required');
    }
    
    return this.apiClient.get<Job>(`/jobs/${encodeURIComponent(jobId)}`);
  }

  /**
   * Cancel a running job
   * @param jobId - The job ID to cancel
   * @returns Promise<CancelJobResponse> Cancellation result
   */
  async cancelJob(jobId: string): Promise<CancelJobResponse> {
    if (!jobId?.trim()) {
      throw new Error('Job ID is required');
    }
    
    return this.apiClient.post<CancelJobResponse>(`/jobs/${encodeURIComponent(jobId)}/cancel`);
  }

  /**
   * Get job execution logs
   * @param jobId - The job ID to get logs for
   * @param tail - Optional number of lines from end
   * @returns Promise<JobLogsResponse> Job logs
   */
  async getJobLogs(jobId: string, tail?: number): Promise<JobLogsResponse> {
    if (!jobId?.trim()) {
      throw new Error('Job ID is required');
    }

    const params = tail ? `?tail=${tail}` : '';
    return this.apiClient.get<JobLogsResponse>(`/jobs/${encodeURIComponent(jobId)}/logs${params}`);
  }

  /**
   * Get job execution context
   * @param jobId - The job ID to get context for
   * @returns Promise<JobContextResponse> Job context
   */
  async getJobContext(jobId: string): Promise<JobContextResponse> {
    if (!jobId?.trim()) {
      throw new Error('Job ID is required');
    }
    
    return this.apiClient.get<JobContextResponse>(`/jobs/${encodeURIComponent(jobId)}/context`);
  }

  /**
   * Check if a job exists
   * @param jobId - The job ID to check
   * @returns Promise<boolean> Whether the job exists
   */
  async jobExists(jobId: string): Promise<boolean> {
    try {
      await this.getJob(jobId);
      return true;
    } catch (error) {
      return false;
    }
  }
}

// Default job service instance
// Use an API base path so we can proxy through Vite (see vite.config.ts -> server.proxy['/api']).
// This avoids collisions with the React dev server returning index.html for unknown paths.
const DEFAULT_ORCH_BASE = typeof window !== 'undefined' ? `${window.location.origin}/api` : 'http://localhost:8000';
export const jobService = new JobService(new ApiClient({ 
  baseUrl: (typeof window !== 'undefined' && (window as any).__ORCH_BASE__) || DEFAULT_ORCH_BASE
}));