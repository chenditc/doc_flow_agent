/**
 * Real-time service for handling Server-Sent Events (SSE) connections
 * Manages real-time trace monitoring and updates
 */

import type { SSEMessage } from '../types';

export interface RealtimeOptions {
  onMessage?: (message: SSEMessage) => void;
  onError?: (error: Error) => void;
  onOpen?: () => void;
  onClose?: () => void;
  onConnectionChange?: (isConnected: boolean, error?: string) => void;
  reconnectInterval?: number;
  maxReconnectAttempts?: number;
  heartbeatInterval?: number;
}

export class RealtimeService {
  private baseUrl: string;
  private eventSource: EventSource | null = null;
  private options: RealtimeOptions;
  private reconnectAttempts = 0;
  private reconnectTimer: NodeJS.Timeout | null = null;
  private heartbeatTimer: NodeJS.Timeout | null = null;
  private isConnected = false;
  private shouldReconnect = false;
  private lastHeartbeat: number = 0;
  private currentTraceId: string | null = null;

  constructor(baseUrl = '', options: RealtimeOptions = {}) {
    this.baseUrl = baseUrl;
    this.options = {
      reconnectInterval: 5000,
      maxReconnectAttempts: 5,
      heartbeatInterval: 30000, // 30 seconds
      ...options,
    };
  }

  /**
   * Start real-time monitoring for a trace
   */
  startMonitoring(traceId: string): void {
    if (!traceId) {
      throw new Error('Trace ID is required');
    }

    this.shouldReconnect = true;
    this.currentTraceId = traceId;
    this.connectToTrace(traceId);
  }

  /**
   * Stop real-time monitoring
   */
  stopMonitoring(): void {
    this.shouldReconnect = false;
    this.currentTraceId = null;
    this.disconnect();
  }

  /**
   * Check if currently connected
   */
  isMonitoring(): boolean {
    return this.isConnected;
  }

  /**
   * Get current connection state
   */
  getConnectionState(): 'connecting' | 'open' | 'closed' | 'error' {
    if (!this.eventSource) {
      return 'closed';
    }

    switch (this.eventSource.readyState) {
      case EventSource.CONNECTING:
        return 'connecting';
      case EventSource.OPEN:
        return 'open';
      case EventSource.CLOSED:
        return 'closed';
      default:
        return 'error';
    }
  }

  /**
   * Update callback options
   */
  updateOptions(newOptions: Partial<RealtimeOptions>): void {
    this.options = { ...this.options, ...newOptions };
  }

  private connectToTrace(traceId: string): void {
    this.disconnect(); // Close any existing connection

    const url = `${this.baseUrl}/traces/${encodeURIComponent(traceId)}/stream`;
    console.log(`Creating SSE connection to: ${url}`);

    try {
      this.eventSource = new EventSource(url);
      this.setupEventHandlers(traceId);
    } catch (error) {
      console.error('Failed to create SSE connection:', error);
      this.handleError(new Error(`Failed to create SSE connection: ${error}`));
    }
  }

  private setupEventHandlers(traceId: string): void {
    if (!this.eventSource) return;

    this.eventSource.onopen = () => {
      console.log(`SSE connection opened for trace: ${traceId}`);
      this.isConnected = true;
      this.reconnectAttempts = 0;
      this.clearReconnectTimer();
      this.startHeartbeat();
      
      if (this.options.onOpen) {
        this.options.onOpen();
      }
      
      if (this.options.onConnectionChange) {
        this.options.onConnectionChange(true);
      }
    };

    this.eventSource.onmessage = (event: MessageEvent) => {
      console.log(`SSE message received:`, event.data);
      this.lastHeartbeat = Date.now();
      
      try {
        const data = JSON.parse(event.data);
        
        // Handle heartbeat messages
        if (data.type === 'heartbeat') {
          console.log('Heartbeat received');
          return;
        }
        
        const message: SSEMessage = {
          type: event.type,
          data,
          timestamp: new Date().toISOString(),
        };
        
        console.log(`Parsed SSE data:`, message);
        
        if (this.options.onMessage) {
          this.options.onMessage(message);
        }
      } catch (parseError) {
        console.error('Error parsing SSE message:', parseError);
        this.handleError(new Error('Invalid SSE message format'));
      }
    };

    this.eventSource.onerror = (error: Event) => {
      console.error('SSE connection error:', error);
      console.error('SSE readyState:', this.eventSource?.readyState);
      
      this.isConnected = false;
      this.stopHeartbeat();
      
      if (this.options.onConnectionChange) {
        this.options.onConnectionChange(false, 'Connection error');
      }
      
      if (this.shouldReconnect && this.reconnectAttempts < (this.options.maxReconnectAttempts || 5)) {
        this.scheduleReconnect(traceId);
      } else {
        this.handleError(new Error(`SSE connection failed after ${this.reconnectAttempts} attempts`));
      }
    };
  }

  private handleError(error: Error): void {
    console.error('RealtimeService error:', error);
    
    if (this.options.onError) {
      this.options.onError(error);
    }
    
    if (this.options.onConnectionChange) {
      this.options.onConnectionChange(false, error.message);
    }
  }

  private scheduleReconnect(_traceId: string): void {
    if (this.reconnectTimer) {
      return; // Already scheduled
    }

    const delay = this.options.reconnectInterval || 5000;
    console.log(`Scheduling reconnect attempt ${this.reconnectAttempts + 1} in ${delay}ms`);
    
    this.reconnectTimer = setTimeout(() => {
      this.reconnectAttempts++;
      this.reconnectTimer = null;
      
      if (this.shouldReconnect && this.currentTraceId) {
        console.log(`Reconnecting to trace ${this.currentTraceId} (attempt ${this.reconnectAttempts})`);
        this.connectToTrace(this.currentTraceId);
      }
    }, delay);
  }

  private clearReconnectTimer(): void {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
  }

  private disconnect(): void {
    this.clearReconnectTimer();
    this.stopHeartbeat();
    
    if (this.eventSource) {
      console.log('Closing SSE connection');
      this.eventSource.close();
      this.eventSource = null;
    }
    
    this.isConnected = false;
    
    if (this.options.onClose) {
      this.options.onClose();
    }
    
    if (this.options.onConnectionChange) {
      this.options.onConnectionChange(false);
    }
  }

  private startHeartbeat(): void {
    this.stopHeartbeat();
    this.lastHeartbeat = Date.now();
    
    if (this.options.heartbeatInterval && this.options.heartbeatInterval > 0) {
      this.heartbeatTimer = setInterval(() => {
        const timeSinceLastBeat = Date.now() - this.lastHeartbeat;
        const timeout = this.options.heartbeatInterval! * 2; // Allow 2x interval before considering disconnected
        
        if (timeSinceLastBeat > timeout) {
          console.warn('Heartbeat timeout detected, connection may be stale');
          this.handleError(new Error('Connection heartbeat timeout'));
        }
      }, this.options.heartbeatInterval);
    }
  }

  private stopHeartbeat(): void {
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer);
      this.heartbeatTimer = null;
    }
  }
}

// Factory function for creating realtime service instances
export const createRealtimeService = (baseUrl = '', options: RealtimeOptions = {}): RealtimeService => {
  return new RealtimeService(baseUrl, options);
};
