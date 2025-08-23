/**
 * Trace-specific API service
 * Handles all trace-related API operations
 */

import type { TraceSession } from '../types';
import { ApiClient } from './api';

export class TraceService {
  private apiClient: ApiClient;

  constructor(apiClient: ApiClient) {
    this.apiClient = apiClient;
  }

  /**
   * Fetch list of available traces
   * @returns Promise<string[]> List of trace IDs
   */
  async getTraces(): Promise<string[]> {
    return this.apiClient.get<string[]>('/traces');
  }

  /**
   * Fetch a specific trace by ID
   * @param traceId - The trace ID to fetch
   * @returns Promise<TraceSession> The trace data
   */
  async getTrace(traceId: string): Promise<TraceSession> {
    if (!traceId) {
      throw new Error('Trace ID is required');
    }
    
    return this.apiClient.get<TraceSession>(`/traces/${encodeURIComponent(traceId)}`);
  }

  /**
   * Fetch the latest trace ID
   * @returns Promise<string> The latest trace ID
   */
  async getLatestTrace(): Promise<string> {
    const result = await this.apiClient.get<{ trace_id: string }>('/traces/latest');
    return result.trace_id;
  }

  /**
   * Check if a trace exists
   * @param traceId - The trace ID to check
   * @returns Promise<boolean> Whether the trace exists
   */
  async traceExists(traceId: string): Promise<boolean> {
    try {
      await this.getTrace(traceId);
      return true;
    } catch (error) {
      return false;
    }
  }

  /**
   * Get trace statistics
   * @param traceId - The trace ID to get statistics for
   * @returns Promise<any> Trace statistics
   */
  async getTraceStatistics(traceId: string): Promise<any> {
    if (!traceId) {
      throw new Error('Trace ID is required');
    }
    
    return this.apiClient.get<any>(`/traces/${encodeURIComponent(traceId)}/statistics`);
  }
}

// Default trace service instance
export const traceService = new TraceService(new ApiClient({ 
  baseUrl: typeof window !== 'undefined' ? window.location.origin : 'http://localhost:8000' 
}));
