/**
 * Formatting utilities for Doc Flow Trace Viewer
 * Handles data transformation and display formatting
 */

/**
 * Safely escape HTML content to prevent XSS
 * @param {any} unsafe - Content to escape
 * @returns {string} HTML-escaped string
 */
function escapeHtml(unsafe) {
    if (!unsafe) return '';
    
    // Convert to string if not already a string
    const str = typeof unsafe === 'string' ? unsafe : String(unsafe);
    
    return str
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

/**
 * Format timestamp for display
 * @param {string} timestamp - ISO timestamp string
 * @returns {string} Formatted time string
 */
function formatTime(timestamp) {
    if (!timestamp) return 'N/A';
    try {
        return new Date(timestamp).toLocaleTimeString();
    } catch (error) {
        return 'Invalid time';
    }
}

/**
 * Calculate duration between start and end times
 * @param {string} startTime - ISO start timestamp
 * @param {string} endTime - ISO end timestamp
 * @returns {string} Formatted duration string
 */
function calculateDuration(startTime, endTime) {
    if (!startTime || !endTime) return 'N/A';
    
    try {
        const start = new Date(startTime);
        const end = new Date(endTime);
        const diffMs = end - start;
        const diffSec = Math.round(diffMs / 1000);
        
        if (diffSec < 60) {
            return `${diffSec}s`;
        } else {
            const minutes = Math.floor(diffSec / 60);
            const seconds = diffSec % 60;
            return `${minutes}m ${seconds}s`;
        }
    } catch (error) {
        return 'Invalid duration';
    }
}

/**
 * Extract task output from trace data
 * @param {Object} task - Task execution object
 * @returns {string} Formatted output text
 */
function extractTaskOutput(task) {
    // First, try to get from engine_state_after.context.last_task_output
    if (task.engine_state_after && 
        task.engine_state_after.context && 
        task.engine_state_after.context.last_task_output) {
        
        const output = task.engine_state_after.context.last_task_output;
        
        // Handle different output formats
        if (typeof output === 'string') {
            return output;
        } else if (typeof output === 'object' && output !== null) {
            // Handle structured output (e.g., {stdout, stderr})
            if (output.stdout || output.stderr) {
                let result = '';
                if (output.stdout) result += output.stdout;
                if (output.stderr) result += (result ? '\n--- STDERR ---\n' : '') + output.stderr;
                return result || 'No output';
            } else {
                // For other objects, stringify them
                return JSON.stringify(output, null, 2);
            }
        }
    }
    
    // Look for context_update phase with updated_paths
    if (task.phases && task.phases.context_update) {
        // Try to find updated context values
        if (task.engine_state_after && task.engine_state_after.context) {
            const context = task.engine_state_after.context;
            // Look for any meaningful output in context
            for (const [key, value] of Object.entries(context)) {
                if (key.includes('output') || key.includes('result') || key === 'last_task_output') {
                    if (typeof value === 'string') {
                        return value;
                    } else if (typeof value === 'object' && value !== null) {
                        if (value.stdout || value.stderr) {
                            let result = '';
                            if (value.stdout) result += value.stdout;
                            if (value.stderr) result += (result ? '\n--- STDERR ---\n' : '') + value.stderr;
                            return result || 'No output';
                        } else {
                            return JSON.stringify(value, null, 2);
                        }
                    }
                }
            }
        }
    }
    
    // Fallback: if there's an error, show that
    if (task.error) {
        return `Error: ${task.error}`;
    }
    
    // Default fallback - show first meaningful context value
    if (task.engine_state_after && task.engine_state_after.context) {
        const contextValues = Object.entries(task.engine_state_after.context);
        for (const [key, value] of contextValues) {
            if (typeof value === 'string' && value.length > 10) {
                return value;
            } else if (typeof value === 'object' && value !== null && key.includes('output')) {
                if (value.stdout || value.stderr) {
                    let result = '';
                    if (value.stdout) result += value.stdout;
                    if (value.stderr) result += (result ? '\n--- STDERR ---\n' : '') + value.stderr;
                    return result || 'No output';
                } else {
                    return JSON.stringify(value, null, 2);
                }
            }
        }
    }
    
    return "No output available";
}

/**
 * Extract phases from trace data
 * @param {Object} task - Task execution object
 * @returns {Array} Array of phase objects
 */
function extractPhases(task) {
    if (!task.phases) return [];
    
    // Convert phases object to array format for rendering
    return Object.entries(task.phases).map(([name, phaseData]) => ({
        name: name.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()),
        status: phaseData.status || 'unknown',
        start_time: phaseData.start_time,
        end_time: phaseData.end_time
    }));
}

/**
 * Truncate long text with ellipsis
 * @param {string} text - Text to truncate
 * @param {number} maxLength - Maximum length before truncation
 * @returns {string} Truncated text
 */
function truncateText(text, maxLength = 500) {
    if (!text || typeof text !== 'string') return '';
    if (text.length <= maxLength) return text;
    return text.substring(0, maxLength) + '...';
}

// Export functions
if (typeof window !== 'undefined') {
    window.FormattingUtils = {
        escapeHtml,
        formatTime,
        calculateDuration,
        extractTaskOutput,
        extractPhases,
        truncateText
    };
}

// Also export for module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        escapeHtml,
        formatTime,
        calculateDuration,
        extractTaskOutput,
        extractPhases,
        truncateText
    };
}
