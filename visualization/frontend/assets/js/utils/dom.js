/**
 * DOM utilities for Doc Flow Trace Viewer
 * Handles DOM manipulation and element creation helpers
 */

/**
 * Show or hide loading indicator
 * @param {boolean} show - Whether to show the loading indicator
 */
function showLoading(show = true) {
    const indicator = document.getElementById('loading-indicator');
    if (indicator) {
        indicator.style.display = show ? 'block' : 'none';
    }
}

/**
 * Show error message
 * @param {string} message - Error message to display
 */
function showError(message) {
    const errorDiv = document.getElementById('error-message');
    if (errorDiv) {
        errorDiv.textContent = message;
        errorDiv.style.display = 'block';
        
        // Hide error after 10 seconds
        setTimeout(() => {
            errorDiv.style.display = 'none';
        }, 10000);
    }
}

/**
 * Hide error message
 */
function hideError() {
    const errorDiv = document.getElementById('error-message');
    if (errorDiv) {
        errorDiv.style.display = 'none';
    }
}

/**
 * Clear the timeline container
 */
function clearTimeline() {
    const timelineContainer = document.getElementById('timeline');
    if (timelineContainer) {
        timelineContainer.innerHTML = '<p class="text-gray-500 text-center py-8">Select a trace to view task executions</p>';
    }
}

/**
 * Create a status badge element
 * @param {string} status - Status value
 * @returns {HTMLElement} Badge element
 */
function createStatusBadge(status) {
    const badge = document.createElement('span');
    badge.className = getStatusClasses(status);
    badge.textContent = status ? String(status).toUpperCase() : 'UNKNOWN';
    return badge;
}

/**
 * Get CSS classes for status badges
 * @param {string} status - Status value
 * @returns {string} CSS classes
 */
function getStatusClasses(status) {
    const base = 'px-2 py-1 rounded text-xs font-medium inline-block ';
    if (!status) return base + 'bg-gray-100 text-gray-700';
    
    const s = String(status).toLowerCase();
    switch (s) {
        case 'completed': return base + 'bg-green-100 text-green-800';
        case 'failed': return base + 'bg-red-100 text-red-800';
        case 'started': return base + 'bg-yellow-100 text-yellow-800';
        case 'retrying': return base + 'bg-orange-100 text-orange-800';
        default: return base + 'bg-gray-100 text-gray-700';
    }
}

/**
 * Create a collapsible details element
 * @param {string} summary - Summary text
 * @param {string} content - Detailed content
 * @returns {HTMLElement} Details element
 */
function createCollapsibleDetails(summary, content) {
    const details = document.createElement('details');
    details.className = 'mt-2';
    
    const summaryEl = document.createElement('summary');
    summaryEl.className = 'cursor-pointer text-sm text-blue-700 font-semibold';
    summaryEl.textContent = summary;
    details.appendChild(summaryEl);
    
    const pre = document.createElement('pre');
    pre.className = 'mt-2 bg-gray-50 p-3 rounded text-sm overflow-auto max-h-64 whitespace-pre-wrap';
    pre.textContent = content;
    
    details.appendChild(pre);
    return details;
}

/**
 * Safely get element by ID with error handling
 * @param {string} id - Element ID
 * @returns {HTMLElement|null} Element or null if not found
 */
function safeGetElementById(id) {
    try {
        return document.getElementById(id);
    } catch (error) {
        console.warn(`Element with ID '${id}' not found:`, error);
        return null;
    }
}

/**
 * Add event listener with error handling
 * @param {HTMLElement} element - Element to add listener to
 * @param {string} event - Event type
 * @param {Function} handler - Event handler function
 */
function safeAddEventListener(element, event, handler) {
    if (!element || typeof handler !== 'function') {
        console.warn('Invalid element or handler for event listener');
        return;
    }
    
    try {
        element.addEventListener(event, handler);
    } catch (error) {
        console.error('Error adding event listener:', error);
    }
}

// Export functions
if (typeof window !== 'undefined') {
    window.DOMUtils = {
        showLoading,
        showError,
        hideError,
        clearTimeline,
        createStatusBadge,
        getStatusClasses,
        createCollapsibleDetails,
        safeGetElementById,
        safeAddEventListener
    };
}

// Also export for module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        showLoading,
        showError,
        hideError,
        clearTimeline,
        createStatusBadge,
        getStatusClasses,
        createCollapsibleDetails,
        safeGetElementById,
        safeAddEventListener
    };
}
