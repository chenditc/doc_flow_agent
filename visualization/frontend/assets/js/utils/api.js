/**
 * API client utilities for Doc Flow Trace Viewer
 * Handles all communication with the backend server
 */

class TraceAPI {
    constructor(baseUrl = '') {
        this.baseUrl = baseUrl;
    }

    /**
     * Fetch list of available traces
     * @returns {Promise<Array<string>>} List of trace IDs
     */
    async getTraces() {
        const response = await fetch(`${this.baseUrl}/traces`);
        if (!response.ok) {
            throw new Error(`Failed to fetch traces: ${response.status} ${response.statusText}`);
        }
        return await response.json();
    }

    /**
     * Fetch a specific trace by ID
     * @param {string} traceId - The trace ID to fetch
     * @returns {Promise<Object>} The trace data
     */
    async getTrace(traceId) {
        if (!traceId) {
            throw new Error('Trace ID is required');
        }
        
        const response = await fetch(`${this.baseUrl}/traces/${encodeURIComponent(traceId)}`);
        if (!response.ok) {
            throw new Error(`Failed to fetch trace: ${response.status} ${response.statusText}`);
        }
        
        try {
            return await response.json();
        } catch (error) {
            throw new Error(`Invalid JSON response: ${error.message}`);
        }
    }

    /**
     * Fetch the latest trace ID
     * @returns {Promise<string>} The latest trace ID
     */
    async getLatestTrace() {
        const response = await fetch(`${this.baseUrl}/traces/latest`);
        if (!response.ok) {
            throw new Error(`Failed to fetch latest trace: ${response.status} ${response.statusText}`);
        }
        
        try {
            const result = await response.json();
            return result.trace_id;
        } catch (error) {
            throw new Error(`Invalid JSON response: ${error.message}`);
        }
    }

    /**
     * Check server health
     * @returns {Promise<Object>} Health status
     */
    async healthCheck() {
        const response = await fetch(`${this.baseUrl}/health`);
        if (!response.ok) {
            throw new Error(`Health check failed: ${response.status} ${response.statusText}`);
        }
        return await response.json();
    }

    /**
     * Start real-time monitoring for a trace using Server-Sent Events
     * @param {string} traceId - The trace ID to monitor
     * @param {Function} onMessage - Callback for incoming messages
     * @param {Function} onError - Callback for errors
     * @returns {EventSource} The EventSource instance
     */
    startRealtimeMonitoring(traceId, onMessage, onError) {
        if (!traceId) {
            throw new Error('Trace ID is required');
        }

        const url = `${this.baseUrl}/traces/${encodeURIComponent(traceId)}/stream`;
        console.log(`Creating SSE connection to: ${url}`);
        const eventSource = new EventSource(url);

        eventSource.onopen = function() {
            console.log(`SSE connection opened for trace: ${traceId}`);
        };

        eventSource.onmessage = function(event) {
            console.log(`SSE message received:`, event.data);
            try {
                const data = JSON.parse(event.data);
                console.log(`Parsed SSE data:`, data);
                if (onMessage) {
                    onMessage(data);
                }
            } catch (error) {
                console.error('Error parsing SSE message:', error);
                if (onError) {
                    onError(new Error('Invalid SSE message format'));
                }
            }
        };

        eventSource.onerror = function(error) {
            console.error('SSE connection error:', error);
            console.error('SSE readyState:', eventSource.readyState);
            if (onError) {
                onError(error);
            }
        };

        return eventSource;
    }
}

// Create default instance
const traceAPI = new TraceAPI();

// Export for use in other scripts
if (typeof window !== 'undefined') {
    window.TraceAPI = TraceAPI;
    window.traceAPI = traceAPI;
}

// Also export for module usage (when using ES6 imports)
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { TraceAPI, traceAPI };
}
