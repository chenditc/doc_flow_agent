/**
 * Timeline component for Doc Flow Trace Viewer
 * Handles rendering and interaction with the task execution timeline
 */

class TimelineComponent {
    constructor() {
        this.currentTrace = null;
        this.onTaskClick = null;
    }

    /**
     * Set callback for task click events
     * @param {Function} callback - Function to call when task is clicked
     */
    setTaskClickHandler(callback) {
        this.onTaskClick = callback;
    }

    /**
     * Render timeline from trace data
     * @param {Object} trace - Trace data object
     */
    render(trace) {
        const previousTaskCount = this.currentTrace ? 
            (this.currentTrace.task_executions ? this.currentTrace.task_executions.length : 0) : 0;
        
        this.currentTrace = trace;
        const timelineContainer = DOMUtils.safeGetElementById('timeline');
        
        if (!timelineContainer) {
            console.error('Timeline container not found');
            return;
        }

        // Clear existing content
        timelineContainer.innerHTML = '';

        // Check if we have task executions
        if (!trace.task_executions || trace.task_executions.length === 0) {
            timelineContainer.innerHTML = '<p class="text-gray-500 text-center py-8">No task executions found in this trace</p>';
            return;
        }

        // Render each task execution
        trace.task_executions.forEach((task, index) => {
            const timelineItem = this.createTaskItem(task, index, trace.task_executions.length);
            
            // Mark new tasks with a visual indicator
            const currentTaskCount = trace.task_executions.length;
            if (currentTaskCount > previousTaskCount && index >= previousTaskCount) {
                timelineItem.classList.add('new-task-indicator');
                // Remove the indicator after animation
                setTimeout(() => {
                    timelineItem.classList.remove('new-task-indicator');
                }, 3000);
            }
            
            timelineContainer.appendChild(timelineItem);
        });
    }

    /**
     * Create a single task timeline item
     * @param {Object} task - Task execution data
     * @param {number} index - Task index
     * @param {number} total - Total number of tasks
     * @returns {HTMLElement} Timeline item element
     */
    createTaskItem(task, index, total) {
        const timelineItem = document.createElement('div');
        timelineItem.className = `timeline-item ${task.status} relative`;
        timelineItem.setAttribute('data-task-id', task.task_execution_id || '');
        timelineItem.style.cursor = 'pointer';

        // Add click handler
        timelineItem.addEventListener('click', (evt) => {
            evt.stopPropagation();
            if (this.onTaskClick) {
                this.onTaskClick(task);
            }
        });

        // Add connector line (except for last item)
        if (index < total - 1) {
            const connector = document.createElement('div');
            connector.className = 'timeline-connector';
            timelineItem.appendChild(connector);
        }

        // Create task content
        const duration = FormattingUtils.calculateDuration(task.start_time, task.end_time);
        const statusBadgeClass = this.getTaskStatusClass(task.status);
        const phases = FormattingUtils.extractPhases(task);
        const output = FormattingUtils.extractTaskOutput(task);

        timelineItem.innerHTML = `
            <div class="bg-gray-50 rounded-lg p-4 border-l-4 ${this.getTaskBorderClass(task.status)}">
                <!-- Task Header -->
                <div class="flex justify-between items-start mb-2">
                    <div class="flex-1">
                        <h3 class="font-medium text-gray-900">${FormattingUtils.escapeHtml(task.task_description)}</h3>
                        <div class="flex items-center space-x-4 mt-1 text-sm text-gray-500">
                            <span>Execution: ${task.task_execution_counter}</span>
                            <span>Started: ${FormattingUtils.formatTime(task.start_time)}</span>
                            <span>Duration: ${duration}</span>
                            <span class="px-2 py-1 rounded-full text-xs font-medium ${statusBadgeClass}">
                                ${task.status ? task.status.toUpperCase() : 'UNKNOWN'}
                            </span>
                        </div>
                    </div>
                </div>

                <!-- Phases -->
                ${this.renderPhases(phases)}

                <!-- Task Output -->
                <div class="mt-3">
                    <h4 class="text-sm font-medium text-gray-700 mb-2">Output:</h4>
                    <pre class="bg-white border rounded p-3 text-sm text-gray-800 overflow-auto max-h-64 whitespace-pre-wrap">${FormattingUtils.escapeHtml(output)}</pre>
                </div>
            </div>
        `;

        return timelineItem;
    }

    /**
     * Render phases section
     * @param {Array} phases - Array of phase objects
     * @returns {string} HTML string for phases
     */
    renderPhases(phases) {
        if (phases.length === 0) return '';

        const phasesHtml = phases.map(phase => {
            const phaseClass = this.getPhaseStatusClass(phase.status);
            const duration = phase.start_time && phase.end_time ? 
                FormattingUtils.calculateDuration(phase.start_time, phase.end_time) : 'N/A';
            
            return `<span class="px-2 py-1 rounded text-xs font-medium ${phaseClass}" title="Duration: ${duration}">${FormattingUtils.escapeHtml(phase.name)}</span>`;
        }).join('');

        return `
            <div class="mb-3">
                <div class="flex flex-wrap gap-2">
                    ${phasesHtml}
                </div>
            </div>
        `;
    }

    /**
     * Get CSS class for task status badge
     * @param {string} status - Task status
     * @returns {string} CSS classes
     */
    getTaskStatusClass(status) {
        switch (status) {
            case 'completed': return 'bg-green-100 text-green-800';
            case 'failed': return 'bg-red-100 text-red-800';
            default: return 'bg-yellow-100 text-yellow-800';
        }
    }

    /**
     * Get CSS class for task border
     * @param {string} status - Task status
     * @returns {string} CSS classes
     */
    getTaskBorderClass(status) {
        switch (status) {
            case 'completed': return 'border-green-400';
            case 'failed': return 'border-red-400';
            default: return 'border-yellow-400';
        }
    }

    /**
     * Get CSS class for phase status badge
     * @param {string} status - Phase status
     * @returns {string} CSS classes
     */
    getPhaseStatusClass(status) {
        switch (status) {
            case 'completed': return 'bg-green-200 text-green-800';
            case 'failed': return 'bg-red-200 text-red-800';
            default: return 'bg-gray-200 text-gray-600';
        }
    }

    /**
     * Clear the timeline
     */
    clear() {
        DOMUtils.clearTimeline();
        this.currentTrace = null;
    }

    /**
     * Scroll timeline to the latest (bottom-most) task
     */
    scrollToLatest() {
        const timelineContainer = DOMUtils.safeGetElementById('timeline');
        if (!timelineContainer) {
            return;
        }

        // Smooth scroll to bottom
        setTimeout(() => {
            timelineContainer.scrollTop = timelineContainer.scrollHeight;
            
            // If the timeline container itself doesn't scroll, scroll the window
            if (timelineContainer.scrollHeight <= timelineContainer.clientHeight) {
                const lastTask = timelineContainer.lastElementChild;
                if (lastTask) {
                    lastTask.scrollIntoView({ behavior: 'smooth', block: 'end' });
                }
            }
        }, 100);
    }
}

// Export for use in other scripts
if (typeof window !== 'undefined') {
    window.TimelineComponent = TimelineComponent;
}

// Also export for module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = TimelineComponent;
}
