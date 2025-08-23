/**
 * API response types for Doc Flow Trace Viewer
 */

export interface ApiError {
  message: string;
  status?: number;
  statusText?: string;
}

export interface HealthCheckResponse {
  status: string;
  timestamp?: string;
}

export interface LatestTraceResponse {
  trace_id: string;
}

export interface SSEMessage {
  type: string;
  data: any;
  timestamp?: string;
}

export interface ApiConfig {
  baseUrl: string;
  timeout?: number;
}

export type ApiResponse<T> = Promise<T>;
