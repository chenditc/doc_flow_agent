/**
 * Trace Selector component for Doc Flow Trace Viewer
 * Handles trace selection and loading functionality
 */

class TraceSelectorComponent {
    constructor() {
        this.availableTraces = [];
        this.onTraceSelected = null;
        this.selectElement = null;
        this.refreshButton = null;
        this.realtimeToggle = null;
        this.liveBadge = null;
        
        // Real-time monitoring state
        this.isRealtimeEnabled = false;
        this.eventSource = null;
        this.currentTraceId = null;
        this.onRealtimeUpdate = null;
        this.realtimeRetryCount = 0;
        this.maxRetries = 3;
        this.retryTimeout = null;
        this.pollInterval = null;
    }

    /**
     * Initialize the trace selector component
     */
    init() {
        this.selectElement = DOMUtils.safeGetElementById('trace-select');
        this.refreshButton = DOMUtils.safeGetElementById('refresh-traces');
        this.realtimeToggle = DOMUtils.safeGetElementById('realtime-toggle');
        this.liveBadge = DOMUtils.safeGetElementById('live-badge');
        this.timelineLiveIndicator = DOMUtils.safeGetElementById('timeline-live-indicator');

        if (!this.selectElement) {
            console.error('Trace select element not found');
            return;
        }

        this.setupEventListeners();
        this.loadTraces();

        // Handle page visibility changes
        document.addEventListener('visibilitychange', () => {
            if (document.hidden && this.isRealtimeEnabled) {
                this.pauseRealtime();
            } else if (!document.hidden && this.realtimeToggle?.checked) {
                this.resumeRealtime();
            }
        });

        // Handle page unload
        window.addEventListener('beforeunload', () => {
            this.stopRealtime();
        });
    }

    /**
     * Set callback for trace selection events
     * @param {Function} callback - Function to call when trace is selected
     */
    setTraceSelectedHandler(callback) {
        this.onTraceSelected = callback;
    }

    /**
     * Set callback for real-time update events
     * @param {Function} callback - Function to call when real-time update occurs
     */
    setRealtimeUpdateHandler(callback) {
        this.onRealtimeUpdate = callback;
    }

    /**
     * Set up event listeners
     */
    setupEventListeners() {
        // Trace selection change
        DOMUtils.safeAddEventListener(this.selectElement, 'change', () => {
            const selectedTraceId = this.selectElement.value;
            
            // Stop current real-time monitoring when switching traces
            if (this.isRealtimeEnabled && this.currentTraceId !== selectedTraceId) {
                this.stopRealtime();
                this.currentTraceId = selectedTraceId;
                
                // Restart real-time monitoring for new trace if toggle is on
                if (this.realtimeToggle?.checked && selectedTraceId) {
                    setTimeout(() => this.startRealtime(), 100);
                }
            } else {
                this.currentTraceId = selectedTraceId;
            }
            
            if (this.onTraceSelected) {
                this.onTraceSelected(selectedTraceId);
            }
        });

        // Refresh button
        if (this.refreshButton) {
            DOMUtils.safeAddEventListener(this.refreshButton, 'click', () => {
                this.loadTraces();
            });
        }

        // Real-time toggle
        if (this.realtimeToggle) {
            DOMUtils.safeAddEventListener(this.realtimeToggle, 'change', () => {
                if (this.realtimeToggle.checked) {
                    this.startRealtime();
                } else {
                    this.stopRealtime();
                }
            });
        }
    }

    /**
     * Load available traces from backend
     */
    async loadTraces() {
        try {
            DOMUtils.showLoading(true);
            DOMUtils.hideError();

            const traces = await traceAPI.getTraces();
            this.availableTraces = traces;

            this.populateDropdown(traces);
            
            // Auto-select latest trace if no trace is currently selected
            const currentSelection = this.getSelectedTraceId();
            if (!currentSelection && traces.length > 0) {
                await this.autoSelectLatestTrace();
            }

            console.log(`Loaded ${traces.length} traces`);

        } catch (error) {
            console.error('Error fetching traces:', error);
            DOMUtils.showError(`Failed to load traces: ${error.message}`);

            // Show retry option
            this.selectElement.innerHTML = '<option value="">Error loading traces - click refresh to retry</option>';
            if (this.refreshButton) {
                this.refreshButton.style.display = 'block';
            }
        } finally {
            DOMUtils.showLoading(false);
        }
    }

    /**
     * Populate the trace selection dropdown
     * @param {Array<string>} traces - Array of trace IDs
     */
    populateDropdown(traces) {
        if (!this.selectElement) return;

        if (traces.length === 0) {
            this.selectElement.innerHTML = '<option value="">No traces found</option>';
            return;
        }

        // Clear existing options and add default
        this.selectElement.innerHTML = '<option value="">Select a trace...</option>';

        // Add trace options (sorted by name for better UX - this will put latest traces first)
        traces.sort().reverse().forEach(traceId => {
            const option = document.createElement('option');
            option.value = traceId;
            // Make display name more readable
            const displayName = traceId.replace(/^session_/, '').replace(/_/g, ' - ');
            option.textContent = displayName;
            this.selectElement.appendChild(option);
        });

        // Hide refresh button since we successfully loaded
        if (this.refreshButton) {
            this.refreshButton.style.display = 'none';
        }
    }

    /**
     * Auto-select the latest trace
     */
    async autoSelectLatestTrace() {
        try {
            const latestTraceId = await traceAPI.getLatestTrace();
            
            // Check if the latest trace is in our available traces
            if (this.availableTraces.includes(latestTraceId)) {
                this.setSelectedTraceId(latestTraceId);
                
                // Trigger the selection event to load the trace
                if (this.onTraceSelected) {
                    this.onTraceSelected(latestTraceId);
                }
                
                console.log(`Auto-selected latest trace: ${latestTraceId}`);
            } else {
                console.warn(`Latest trace ${latestTraceId} not found in available traces`);
            }
        } catch (error) {
            console.error('Failed to auto-select latest trace:', error);
            // Don't show error to user since this is automatic behavior
        }
    }

    /**
     * Get currently selected trace ID
     * @returns {string} Selected trace ID
     */
    getSelectedTraceId() {
        return this.selectElement ? this.selectElement.value : '';
    }

    /**
     * Set selected trace ID
     * @param {string} traceId - Trace ID to select
     */
    setSelectedTraceId(traceId) {
        if (this.selectElement) {
            this.selectElement.value = traceId;
        }
    }

    /**
     * Get list of available traces
     * @returns {Array<string>} Array of trace IDs
     */
    getAvailableTraces() {
        return [...this.availableTraces];
    }

    /**
     * Start real-time monitoring for current trace
     */
    startRealtime() {
        const traceId = this.getSelectedTraceId();
        console.log('startRealtime called, selected trace ID:', traceId);
        
        if (!traceId) {
            console.warn('Cannot start real-time monitoring: no trace selected');
            if (this.realtimeToggle) {
                this.realtimeToggle.checked = false;
            }
            return;
        }

        if (this.isRealtimeEnabled && this.currentTraceId === traceId) {
            console.log('Real-time monitoring already active for this trace');
            return;
        }

        console.log(`Starting real-time monitoring for trace: ${traceId}`);

        // Stop any existing monitoring
        this.stopRealtime();

        this.currentTraceId = traceId;
        this.isRealtimeEnabled = true;
        this.realtimeRetryCount = 0;

        // Update UI
        this.updateRealtimeUI(true);

        // Start SSE connection
        console.log('About to connect SSE...');
        this.connectSSE();
    }

    /**
     * Stop real-time monitoring
     */
    stopRealtime() {
        console.log('Stopping real-time monitoring');

        this.isRealtimeEnabled = false;
        this.currentTraceId = null;

        // Close SSE connection
        if (this.eventSource) {
            this.eventSource.close();
            this.eventSource = null;
        }

        // Clear any retry timeouts
        if (this.retryTimeout) {
            clearTimeout(this.retryTimeout);
            this.retryTimeout = null;
        }

        // Clear fallback polling
        if (this.pollInterval) {
            clearInterval(this.pollInterval);
            this.pollInterval = null;
        }

        // Update UI
        this.updateRealtimeUI(false);
    }

    /**
     * Pause real-time monitoring (for page visibility changes)
     */
    pauseRealtime() {
        if (this.isRealtimeEnabled) {
            console.log('Pausing real-time monitoring');
            if (this.eventSource) {
                this.eventSource.close();
                this.eventSource = null;
            }
            if (this.pollInterval) {
                clearInterval(this.pollInterval);
                this.pollInterval = null;
            }
        }
    }

    /**
     * Resume real-time monitoring (after page becomes visible)
     */
    resumeRealtime() {
        if (this.isRealtimeEnabled && this.currentTraceId) {
            console.log('Resuming real-time monitoring');
            this.connectSSE();
        }
    }

    /**
     * Connect to SSE stream
     */
    connectSSE() {
        if (!this.currentTraceId) return;

        try {
            this.eventSource = traceAPI.startRealtimeMonitoring(
                this.currentTraceId,
                (message) => this.handleRealtimeMessage(message),
                (error) => this.handleRealtimeError(error)
            );
        } catch (error) {
            console.error('Failed to start SSE connection:', error);
            this.startFallbackPolling();
        }
    }

    /**
     * Handle incoming real-time messages
     */
    handleRealtimeMessage(message) {
        console.log('Received real-time message:', message);

        if (message.event === 'file_updated' && this.onRealtimeUpdate) {
            // Debounce updates to avoid excessive API calls
            if (this.updateDebounceTimeout) {
                clearTimeout(this.updateDebounceTimeout);
            }

            this.updateDebounceTimeout = setTimeout(() => {
                this.onRealtimeUpdate(message.trace_id);
            }, 500);
        } else if (message.event === 'connected') {
            console.log(`Connected to real-time stream for trace: ${message.trace_id}`);
            this.realtimeRetryCount = 0; // Reset retry count on successful connection
        }
    }

    /**
     * Handle real-time monitoring errors
     */
    handleRealtimeError(error) {
        console.error('Real-time monitoring error:', error);

        if (this.isRealtimeEnabled) {
            this.realtimeRetryCount++;

            if (this.realtimeRetryCount <= this.maxRetries) {
                const retryDelay = Math.pow(2, this.realtimeRetryCount) * 1000; // Exponential backoff
                console.log(`Retrying SSE connection in ${retryDelay}ms (attempt ${this.realtimeRetryCount}/${this.maxRetries})`);

                this.retryTimeout = setTimeout(() => {
                    if (this.isRealtimeEnabled) {
                        this.connectSSE();
                    }
                }, retryDelay);
            } else {
                console.warn('Max SSE retries reached, falling back to polling');
                this.startFallbackPolling();
            }
        }
    }

    /**
     * Start fallback polling when SSE fails
     */
    startFallbackPolling() {
        if (!this.isRealtimeEnabled || this.pollInterval) return;

        console.log('Starting fallback polling every 5 seconds');
        this.pollInterval = setInterval(() => {
            if (this.isRealtimeEnabled && this.onRealtimeUpdate) {
                this.onRealtimeUpdate(this.currentTraceId);
            }
        }, 5000);
    }

    /**
     * Update real-time monitoring UI
     */
    updateRealtimeUI(isActive) {
        // Update live badge in trace selector
        if (this.liveBadge) {
            if (isActive) {
                this.liveBadge.classList.remove('hidden');
            } else {
                this.liveBadge.classList.add('hidden');
            }
        }

        // Update live indicator in timeline header
        if (this.timelineLiveIndicator) {
            if (isActive) {
                this.timelineLiveIndicator.classList.remove('hidden');
            } else {
                this.timelineLiveIndicator.classList.add('hidden');
            }
        }

        // Update toggle state if needed
        if (this.realtimeToggle && this.realtimeToggle.checked !== isActive) {
            this.realtimeToggle.checked = isActive;
        }
    }

    /**
     * Check if real-time monitoring is active
     */
    isRealtimeActive() {
        return this.isRealtimeEnabled;
    }
}

// Export for use in other scripts
if (typeof window !== 'undefined') {
    window.TraceSelectorComponent = TraceSelectorComponent;
}

// Also export for module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = TraceSelectorComponent;
}
