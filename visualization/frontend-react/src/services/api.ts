/**
 * Core API client for Doc Flow Trace Viewer
 * TypeScript refactored version of the original vanilla JS API
 */

import type { ApiConfig, ApiResponse, HealthCheckResponse } from '../types';

export class ApiClient {
  private baseUrl: string;
  private timeout: number;

  constructor(config: ApiConfig = { baseUrl: '' }) {
    this.baseUrl = config.baseUrl;
    this.timeout = config.timeout || 30000;
  }

  /**
   * Generic fetch wrapper with error handling
   */
  private async fetchWithErrorHandling<T>(url: string, options?: RequestInit): ApiResponse<T> {
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), this.timeout);

      const response = await fetch(`${this.baseUrl}${url}`, {
        ...options,
        signal: controller.signal,
        headers: {
          'Content-Type': 'application/json',
          ...options?.headers,
        },
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        throw new ApiError(`Request failed: ${response.status} ${response.statusText}`, response.status, response.statusText);
      }

      try {
        return await response.json();
      } catch (parseError) {
        throw new ApiError(`Invalid JSON response: ${(parseError as Error).message}`);
      }
    } catch (error) {
      if (error instanceof ApiError) {
        throw error;
      }
      
      if (error instanceof Error) {
        if (error.name === 'AbortError') {
          throw new ApiError(`Request timeout after ${this.timeout}ms`);
        }
        throw new ApiError(`Network error: ${error.message}`);
      }
      
      throw new ApiError('Unknown error occurred');
    }
  }

  /**
   * Check server health
   */
  async healthCheck(): ApiResponse<HealthCheckResponse> {
    return this.fetchWithErrorHandling<HealthCheckResponse>('/health');
  }

  /**
   * Generic GET request
   */
  async get<T>(path: string): ApiResponse<T> {
    return this.fetchWithErrorHandling<T>(path);
  }

  /**
   * Generic POST request
   */
  async post<T>(path: string, data?: any): ApiResponse<T> {
    return this.fetchWithErrorHandling<T>(path, {
      method: 'POST',
      body: data ? JSON.stringify(data) : undefined,
    });
  }

  /**
   * Generic PUT request
   */
  async put<T>(path: string, data?: any): ApiResponse<T> {
    return this.fetchWithErrorHandling<T>(path, {
      method: 'PUT',
      body: data ? JSON.stringify(data) : undefined,
    });
  }

  /**
   * Generic DELETE request
   */
  async delete<T>(path: string): ApiResponse<T> {
    return this.fetchWithErrorHandling<T>(path, {
      method: 'DELETE',
    });
  }
}

// Custom error class for API errors
class ApiError extends Error {
  public status?: number;
  public statusText?: string;

  constructor(message: string, status?: number, statusText?: string) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.statusText = statusText;
  }
}

// Default API client instance
export const apiClient = new ApiClient({ 
  baseUrl: typeof window !== 'undefined' ? window.location.origin : 'http://localhost:8000' 
});

export { ApiError };
