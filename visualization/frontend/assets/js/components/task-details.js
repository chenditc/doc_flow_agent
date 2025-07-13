/**
 * Task Details Modal component for Doc Flow Trace Viewer
 * Handles modal display and interaction for task execution details
 */

class TaskDetailsComponent {
    constructor() {
        this.modal = null;
        this.isInitialized = false;
        this.sopResolutionViewer = new SOPResolutionViewer();
        this.llmCallComponent = new LLMCallComponent();
    }

    /**
     * Initialize the modal component and set up event listeners
     */
    init() {
        if (this.isInitialized) return;

        this.modal = DOMUtils.safeGetElementById('task-details-modal');
        if (!this.modal) {
            console.error('Task details modal not found in DOM');
            return;
        }

        this.setupEventListeners();
        this.isInitialized = true;
    }

    /**
     * Set up event listeners for modal interactions
     */
    setupEventListeners() {
        // Close button
        const closeBtn = DOMUtils.safeGetElementById('task-details-close');
        if (closeBtn) {
            DOMUtils.safeAddEventListener(closeBtn, 'click', () => this.hide());
        }

        // Click outside to close
        DOMUtils.safeAddEventListener(this.modal, 'click', (e) => {
            if (e.target === this.modal) {
                this.hide();
            }
        });

        // Escape key to close
        DOMUtils.safeAddEventListener(document, 'keydown', (e) => {
            if (e.key === 'Escape' && this.isVisible()) {
                this.hide();
            }
        });
    }

    /**
     * Show task details in modal
     * @param {Object} task - Task execution data
     */
    show(task) {
        if (!this.isInitialized) {
            console.error('TaskDetailsComponent not initialized');
            return;
        }

        this.populateContent(task);
        this.modal.classList.remove('hidden');
        this.modal.setAttribute('aria-hidden', 'false');
        document.body.style.overflow = 'hidden';

        // Focus the close button for accessibility
        const closeBtn = DOMUtils.safeGetElementById('task-details-close');
        if (closeBtn) {
            closeBtn.focus();
        }
    }

    /**
     * Hide the modal
     */
    hide() {
        if (!this.modal) return;

        this.modal.classList.add('hidden');
        this.modal.setAttribute('aria-hidden', 'true');
        document.body.style.overflow = '';
    }

    /**
     * Check if modal is currently visible
     * @returns {boolean} True if modal is visible
     */
    isVisible() {
        if (!this.modal) return false;
        return !this.modal.classList.contains('hidden');
    }

    /**
     * Populate modal content with task data
     * @param {Object} task - Task execution data
     */
    populateContent(task) {
        const titleEl = DOMUtils.safeGetElementById('task-details-title');
        const summaryEl = DOMUtils.safeGetElementById('task-details-summary');
        const outputEl = DOMUtils.safeGetElementById('task-details-output');
        const phasesContainer = DOMUtils.safeGetElementById('task-details-phases');

        if (!titleEl || !summaryEl || !outputEl || !phasesContainer) {
            console.error('Required modal elements not found');
            return;
        }

        // Set title
        titleEl.textContent = task.task_description || ('Task ' + (task.task_execution_id || ''));

        // Populate summary
        this.renderSummary(summaryEl, task);

        // Populate output
        this.renderOutput(outputEl, task);

        // Populate phases
        this.renderPhases(phasesContainer, task);
    }

    /**
     * Render task summary section
     * @param {HTMLElement} container - Summary container element
     * @param {Object} task - Task execution data
     */
    renderSummary(container, task) {
        container.innerHTML = '';

        const meta = document.createElement('div');
        meta.className = 'text-sm text-gray-700 space-y-1';

        // Execution counter
        const executionRow = document.createElement('div');
        executionRow.innerHTML = `<strong>Execution:</strong> ${FormattingUtils.escapeHtml(task.task_execution_counter || '')}`;
        meta.appendChild(executionRow);

        // Start time
        const startedRow = document.createElement('div');
        startedRow.innerHTML = `<strong>Started:</strong> ${FormattingUtils.escapeHtml(FormattingUtils.formatTime(task.start_time))}`;
        meta.appendChild(startedRow);

        // End time
        const endedRow = document.createElement('div');
        endedRow.innerHTML = `<strong>Ended:</strong> ${FormattingUtils.escapeHtml(FormattingUtils.formatTime(task.end_time))}`;
        meta.appendChild(endedRow);

        // Duration
        const durRow = document.createElement('div');
        durRow.innerHTML = `<strong>Duration:</strong> ${FormattingUtils.escapeHtml(FormattingUtils.calculateDuration(task.start_time, task.end_time))}`;
        meta.appendChild(durRow);

        // Error (if present)
        if (task.error) {
            const errorRow = document.createElement('div');
            errorRow.className = 'text-red-600';
            errorRow.innerHTML = `<strong>Error:</strong> ${FormattingUtils.escapeHtml(task.error)}`;
            meta.appendChild(errorRow);
        }

        // Status badge
        const statusRow = document.createElement('div');
        statusRow.appendChild(document.createTextNode('Status: '));
        statusRow.appendChild(DOMUtils.createStatusBadge(task.status));
        meta.appendChild(statusRow);

        container.appendChild(meta);
    }

    /**
     * Render task output section
     * @param {HTMLElement} container - Output container element
     * @param {Object} task - Task execution data
     */
    renderOutput(container, task) {
        container.innerHTML = '';

        const header = document.createElement('h3');
        header.className = 'text-lg font-semibold text-gray-900 mb-3';
        header.textContent = 'Task Output';
        container.appendChild(header);

        const output = FormattingUtils.extractTaskOutput(task);
        
        const outputContainer = document.createElement('div');
        outputContainer.className = 'bg-gray-50 border rounded p-4';
        
        const outputPre = document.createElement('pre');
        outputPre.className = 'text-sm text-gray-800 overflow-auto whitespace-pre-wrap max-h-96';
        outputPre.textContent = output;
        
        outputContainer.appendChild(outputPre);
        container.appendChild(outputContainer);
    }

    /**
     * Render phases section
     * @param {HTMLElement} container - Phases container element
     * @param {Object} task - Task execution data
     */
    renderPhases(container, task) {
        container.innerHTML = '';

        const phases = task.phases || {};
        const phaseNames = Object.keys(phases);

        if (phaseNames.length === 0) {
            container.innerHTML = '<p class="text-sm text-gray-500">No phase information available.</p>';
            return;
        }

        phaseNames.forEach((phaseName) => {
            const phaseData = phases[phaseName] || {};
            const phaseElement = this.createPhaseElement(phaseName, phaseData);
            container.appendChild(phaseElement);
        });
    }

    /**
     * Create a single phase element
     * @param {string} phaseName - Name of the phase
     * @param {Object} phaseData - Phase data object
     * @returns {HTMLElement} Phase element
     */
    createPhaseElement(phaseName, phaseData) {
        // Use specialized viewer for SOP resolution phase
        if (phaseName === 'sop_resolution') {
            return this.createSOPResolutionPhaseElement(phaseData);
        }

        // Default phase element for other phases
        const block = document.createElement('div');
        block.className = 'mb-3 p-3 border rounded';

        // Header
        const header = document.createElement('div');
        header.className = 'flex justify-between items-center';

        const left = document.createElement('div');
        left.className = 'flex items-center gap-3';

        const nameEl = document.createElement('div');
        nameEl.className = 'font-medium';
        nameEl.textContent = phaseName.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());

        left.appendChild(nameEl);
        left.appendChild(DOMUtils.createStatusBadge(phaseData.status));

        header.appendChild(left);

        const right = document.createElement('div');
        right.className = 'text-sm text-gray-500';
        right.textContent = `${FormattingUtils.formatTime(phaseData.start_time)} - ${FormattingUtils.formatTime(phaseData.end_time)} (${FormattingUtils.calculateDuration(phaseData.start_time, phaseData.end_time)})`;

        header.appendChild(right);
        block.appendChild(header);

        // Details section
        const detailsData = this.stripMetaFields(phaseData);
        if (Object.keys(detailsData).length > 0) {
            const details = DOMUtils.createCollapsibleDetails(
                'View details (JSON)',
                JSON.stringify(detailsData, null, 2)
            );
            block.appendChild(details);
        }

        return block;
    }

    /**
     * Create specialized SOP resolution phase element
     * @param {Object} phaseData - SOP resolution phase data
     * @returns {HTMLElement} SOP resolution phase element
     */
    createSOPResolutionPhaseElement(phaseData) {
        const block = document.createElement('div');
        block.className = 'mb-3 border rounded';

        // Phase header (similar to other phases)
        const header = document.createElement('div');
        header.className = 'flex justify-between items-center p-3 border-b bg-gray-50';

        const left = document.createElement('div');
        left.className = 'flex items-center gap-3';

        const nameEl = document.createElement('div');
        nameEl.className = 'font-medium';
        nameEl.textContent = 'SOP Resolution';

        left.appendChild(nameEl);
        left.appendChild(DOMUtils.createStatusBadge(phaseData.status));

        header.appendChild(left);

        const right = document.createElement('div');
        right.className = 'text-sm text-gray-500';
        right.textContent = `${FormattingUtils.formatTime(phaseData.start_time)} - ${FormattingUtils.formatTime(phaseData.end_time)} (${FormattingUtils.calculateDuration(phaseData.start_time, phaseData.end_time)})`;

        header.appendChild(right);
        block.appendChild(header);

        // SOP resolution content
        const content = document.createElement('div');
        content.className = 'p-3';

        const sopResolutionElement = this.sopResolutionViewer.createSOPResolutionElement(phaseData);
        content.appendChild(sopResolutionElement);

        block.appendChild(content);

        return block;
    }

    /**
     * Remove meta fields from phase data for display
     * @param {Object} obj - Phase data object
     * @returns {Object} Cleaned phase data
     */
    stripMetaFields(obj) {
        try {
            const clone = JSON.parse(JSON.stringify(obj || {}));
            delete clone.start_time;
            delete clone.end_time;
            delete clone.status;
            return clone;
        } catch (e) {
            return {};
        }
    }
}

// Export for use in other scripts
if (typeof window !== 'undefined') {
    window.TaskDetailsComponent = TaskDetailsComponent;
}

// Also export for module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = TaskDetailsComponent;
}
