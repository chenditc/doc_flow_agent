/**
 * Main application controller for Doc Flow Trace Viewer
 * Coordinates all components and handles application state
 */

class TraceViewerApp {
    constructor() {
        this.timeline = new TimelineComponent();
        this.taskDetails = new TaskDetailsComponent();
        this.traceSelector = new TraceSelectorComponent();
        this.currentTrace = null;
    }

    /**
     * Initialize the application
     */
    init() {
        console.log('Initializing Doc Flow Trace Viewer - Phase 6 (Real-time Monitoring)');

        // Initialize components
        this.timeline.setTaskClickHandler((task) => this.handleTaskClick(task));
        this.taskDetails.init();
        this.traceSelector.setTraceSelectedHandler((traceId) => this.handleTraceSelected(traceId));
        this.traceSelector.setRealtimeUpdateHandler((traceId) => this.handleRealtimeUpdate(traceId));
        this.traceSelector.init();
    }

    /**
     * Handle task click events
     * @param {Object} task - Task execution data
     */
    handleTaskClick(task) {
        this.taskDetails.show(task);
    }

    /**
     * Handle trace selection events
     * @param {string} traceId - Selected trace ID
     */
    async handleTraceSelected(traceId) {
        if (!traceId) {
            this.currentTrace = null;
            this.timeline.clear();
            return;
        }

        try {
            DOMUtils.showLoading(true);
            DOMUtils.hideError();

            const trace = await traceAPI.getTrace(traceId);
            this.currentTrace = trace;

            // Render timeline with real data
            this.timeline.render(trace);

            console.log(`Loaded trace: ${traceId}`, trace);

        } catch (error) {
            console.error('Error fetching trace:', error);
            DOMUtils.showError(`Failed to load trace: ${error.message}`);
            this.currentTrace = null;
            this.timeline.clear();
        } finally {
            DOMUtils.showLoading(false);
        }
    }

    /**
     * Get current trace data
     * @returns {Object|null} Current trace data or null
     */
    getCurrentTrace() {
        return this.currentTrace;
    }

    /**
     * Refresh current trace
     */
    async refreshCurrentTrace() {
        const currentTraceId = this.traceSelector.getSelectedTraceId();
        if (currentTraceId) {
            await this.handleTraceSelected(currentTraceId);
        }
    }

    /**
     * Refresh available traces
     */
    async refreshTraces() {
        await this.traceSelector.loadTraces();
    }

    /**
     * Handle real-time trace updates
     * @param {string} traceId - Updated trace ID
     */
    async handleRealtimeUpdate(traceId) {
        console.log(`handleRealtimeUpdate called with traceId: ${traceId}`);
        
        // Only update if this is the currently selected trace
        const currentTraceId = this.traceSelector.getSelectedTraceId();
        console.log(`Current selected trace: ${currentTraceId}`);
        
        if (traceId !== currentTraceId) {
            console.log(`Ignoring update for different trace: ${traceId} != ${currentTraceId}`);
            return;
        }

        console.log(`Real-time update received for trace: ${traceId}`);

        try {
            // Reload the trace data
            console.log('Fetching updated trace data...');
            const trace = await traceAPI.getTrace(traceId);
            const previousTaskCount = this.currentTrace ? 
                (this.currentTrace.task_executions ? this.currentTrace.task_executions.length : 0) : 0;
            
            this.currentTrace = trace;

            // Update timeline with new data
            console.log('Updating timeline with new data...');
            this.timeline.render(trace);

            // Check if new tasks were added
            const currentTaskCount = trace.task_executions ? trace.task_executions.length : 0;
            console.log(`Task count: ${previousTaskCount} -> ${currentTaskCount}`);
            if (currentTaskCount > previousTaskCount) {
                // Auto-scroll to latest task and add visual indicator
                this.timeline.scrollToLatest();
                console.log(`${currentTaskCount - previousTaskCount} new task(s) added to timeline`);
            }

        } catch (error) {
            console.error('Error handling real-time update:', error);
            // Don't show error to user for real-time updates since they're automatic
        }
    }
}

// Export for use in other scripts
if (typeof window !== 'undefined') {
    window.TraceViewerApp = TraceViewerApp;
}

// Also export for module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = TraceViewerApp;
}
