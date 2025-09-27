/**
 * Unit tests for JobService
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { JobService } from '../services/jobService';
import { ApiClient } from '../services/api';
import type { SubmitJobRequest, JobListFilters } from '../types';

// Mock ApiClient
const mockApiClient = {
  get: vi.fn(),
  post: vi.fn(),
} as unknown as ApiClient;

describe('JobService', () => {
  let jobService: JobService;

  beforeEach(() => {
    vi.clearAllMocks();
    jobService = new JobService(mockApiClient);
  });

  describe('submitJob', () => {
    it('should submit a job successfully', async () => {
      const mockRequest: SubmitJobRequest = {
        task_description: 'Test task',
        max_tasks: 10
      };
      const mockResponse = { job_id: 'test-job-123', status: 'QUEUED' };

      vi.mocked(mockApiClient.post).mockResolvedValue(mockResponse);

      const result = await jobService.submitJob(mockRequest);

      expect(mockApiClient.post).toHaveBeenCalledWith('/jobs', mockRequest);
      expect(result).toEqual(mockResponse);
    });

    it('should throw error for empty task description', async () => {
      const mockRequest: SubmitJobRequest = {
        task_description: '',
        max_tasks: 10
      };

      await expect(jobService.submitJob(mockRequest)).rejects.toThrow('Task description is required');
      expect(mockApiClient.post).not.toHaveBeenCalled();
    });

    it('should throw error for whitespace-only task description', async () => {
      const mockRequest: SubmitJobRequest = {
        task_description: '   ',
        max_tasks: 10
      };

      await expect(jobService.submitJob(mockRequest)).rejects.toThrow('Task description is required');
      expect(mockApiClient.post).not.toHaveBeenCalled();
    });
  });

  describe('listJobs', () => {
    it('should list jobs without filters', async () => {
      const mockJobs = [
        { job_id: 'job1', status: 'COMPLETED', task_description: 'Task 1' },
        { job_id: 'job2', status: 'RUNNING', task_description: 'Task 2' }
      ];

      vi.mocked(mockApiClient.get).mockResolvedValue(mockJobs);

      const result = await jobService.listJobs();

      expect(mockApiClient.get).toHaveBeenCalledWith('/jobs');
      expect(result).toEqual(mockJobs);
    });

    it('should list jobs with status filter', async () => {
      const filters: JobListFilters = { status: 'RUNNING' };
      const mockJobs = [
        { job_id: 'job2', status: 'RUNNING', task_description: 'Task 2' }
      ];

      vi.mocked(mockApiClient.get).mockResolvedValue(mockJobs);

      const result = await jobService.listJobs(filters);

      expect(mockApiClient.get).toHaveBeenCalledWith('/jobs?status=RUNNING');
      expect(result).toEqual(mockJobs);
    });

    it('should list jobs with limit filter', async () => {
      const filters: JobListFilters = { limit: 5 };
      const mockJobs = [
        { job_id: 'job1', status: 'COMPLETED', task_description: 'Task 1' }
      ];

      vi.mocked(mockApiClient.get).mockResolvedValue(mockJobs);

      const result = await jobService.listJobs(filters);

      expect(mockApiClient.get).toHaveBeenCalledWith('/jobs?limit=5');
      expect(result).toEqual(mockJobs);
    });

    it('should list jobs with both status and limit filters', async () => {
      const filters: JobListFilters = { status: 'COMPLETED', limit: 10 };
      const mockJobs = [
        { job_id: 'job1', status: 'COMPLETED', task_description: 'Task 1' }
      ];

      vi.mocked(mockApiClient.get).mockResolvedValue(mockJobs);

      const result = await jobService.listJobs(filters);

      expect(mockApiClient.get).toHaveBeenCalledWith('/jobs?status=COMPLETED&limit=10');
      expect(result).toEqual(mockJobs);
    });
  });

  describe('getJob', () => {
    it('should get a job by ID', async () => {
      const jobId = 'test-job-123';
      const mockJob = {
        job_id: jobId,
        status: 'COMPLETED',
        task_description: 'Test task',
        created_at: '2024-01-01T00:00:00Z',
        trace_files: []
      };

      vi.mocked(mockApiClient.get).mockResolvedValue(mockJob);

      const result = await jobService.getJob(jobId);

      expect(mockApiClient.get).toHaveBeenCalledWith(`/jobs/${jobId}`);
      expect(result).toEqual(mockJob);
    });

    it('should throw error for empty job ID', async () => {
      await expect(jobService.getJob('')).rejects.toThrow('Job ID is required');
      expect(mockApiClient.get).not.toHaveBeenCalled();
    });

    it('should throw error for whitespace-only job ID', async () => {
      await expect(jobService.getJob('   ')).rejects.toThrow('Job ID is required');
      expect(mockApiClient.get).not.toHaveBeenCalled();
    });
  });

  describe('cancelJob', () => {
    it('should cancel a job successfully', async () => {
      const jobId = 'test-job-123';
      const mockResponse = {
        job_id: jobId,
        status: 'CANCELLED',
        cancelled: true
      };

      vi.mocked(mockApiClient.post).mockResolvedValue(mockResponse);

      const result = await jobService.cancelJob(jobId);

      expect(mockApiClient.post).toHaveBeenCalledWith(`/jobs/${jobId}/cancel`);
      expect(result).toEqual(mockResponse);
    });

    it('should throw error for empty job ID', async () => {
      await expect(jobService.cancelJob('')).rejects.toThrow('Job ID is required');
      expect(mockApiClient.post).not.toHaveBeenCalled();
    });
  });

  describe('getJobLogs', () => {
    it('should get job logs without tail parameter', async () => {
      const jobId = 'test-job-123';
      const mockLogs = {
        job_id: jobId,
        logs: 'Log line 1\nLog line 2\n'
      };

      vi.mocked(mockApiClient.get).mockResolvedValue(mockLogs);

      const result = await jobService.getJobLogs(jobId);

      expect(mockApiClient.get).toHaveBeenCalledWith(`/jobs/${jobId}/logs`);
      expect(result).toEqual(mockLogs);
    });

    it('should get job logs with tail parameter', async () => {
      const jobId = 'test-job-123';
      const tail = 100;
      const mockLogs = {
        job_id: jobId,
        logs: 'Recent log line\n'
      };

      vi.mocked(mockApiClient.get).mockResolvedValue(mockLogs);

      const result = await jobService.getJobLogs(jobId, tail);

      expect(mockApiClient.get).toHaveBeenCalledWith(`/jobs/${jobId}/logs?tail=100`);
      expect(result).toEqual(mockLogs);
    });

    it('should throw error for empty job ID', async () => {
      await expect(jobService.getJobLogs('')).rejects.toThrow('Job ID is required');
      expect(mockApiClient.get).not.toHaveBeenCalled();
    });
  });

  describe('jobExists', () => {
    it('should return true if job exists', async () => {
      const jobId = 'test-job-123';
      const mockJob = { job_id: jobId, status: 'COMPLETED' };

      vi.mocked(mockApiClient.get).mockResolvedValue(mockJob);

      const result = await jobService.jobExists(jobId);

      expect(result).toBe(true);
      expect(mockApiClient.get).toHaveBeenCalledWith(`/jobs/${jobId}`);
    });

    it('should return false if job does not exist', async () => {
      const jobId = 'nonexistent-job';

      vi.mocked(mockApiClient.get).mockRejectedValue(new Error('Job not found'));

      const result = await jobService.jobExists(jobId);

      expect(result).toBe(false);
      expect(mockApiClient.get).toHaveBeenCalledWith(`/jobs/${jobId}`);
    });
  });
});