/**
 * LLM Call component for Doc Flow Trace Viewer
 * Reusable component for displaying LLM call details (prompt, response, timing)
 */

class LLMCallComponent {
    constructor() {
        // No persistent state needed
    }

    /**
     * Create an LLM call display element
     * @param {Object} llmCall - LLM call data object
     * @param {string} title - Title for the LLM call section
     * @returns {HTMLElement} LLM call element
     */
    createLLMCallElement(llmCall, title = 'LLM Call') {
        if (!llmCall) {
            return this._createNoDataElement('No LLM call data available');
        }

        const container = document.createElement('div');
        container.className = 'llm-call-container bg-blue-50 border border-blue-200 rounded p-4 mb-4';

        // Header with title and timing
        const header = document.createElement('div');
        header.className = 'llm-call-header flex justify-between items-center mb-3';

        const titleEl = document.createElement('h4');
        titleEl.className = 'text-md font-semibold text-blue-800';
        titleEl.textContent = title;

        const timing = document.createElement('div');
        timing.className = 'text-sm text-gray-600';
        
        if (llmCall.start_time && llmCall.end_time) {
            const duration = FormattingUtils.calculateDuration(llmCall.start_time, llmCall.end_time);
            timing.textContent = `Duration: ${duration}`;
        } else if (llmCall.execution_time_ms) {
            timing.textContent = `Duration: ${Math.round(llmCall.execution_time_ms)}ms`;
        }

        header.appendChild(titleEl);
        header.appendChild(timing);
        container.appendChild(header);

        // Step identifier (if available)
        if (llmCall.step) {
            const stepEl = document.createElement('div');
            stepEl.className = 'text-sm text-gray-600 mb-2';
            stepEl.innerHTML = `<strong>Step:</strong> ${FormattingUtils.escapeHtml(llmCall.step)}`;
            container.appendChild(stepEl);
        }

        // Model info (if available)
        if (llmCall.model) {
            const modelEl = document.createElement('div');
            modelEl.className = 'text-sm text-gray-600 mb-2';
            modelEl.innerHTML = `<strong>Model:</strong> ${FormattingUtils.escapeHtml(llmCall.model)}`;
            container.appendChild(modelEl);
        }

        // Token usage (if available)
        if (llmCall.token_usage) {
            const tokensEl = document.createElement('div');
            tokensEl.className = 'text-sm text-gray-600 mb-2';
            tokensEl.innerHTML = `<strong>Tokens:</strong> ${FormattingUtils.escapeHtml(JSON.stringify(llmCall.token_usage))}`;
            container.appendChild(tokensEl);
        }

        // Prompt section
        if (llmCall.prompt) {
            const promptSection = this._createExpandableSection(
                'Prompt', 
                llmCall.prompt,
                'bg-gray-100 border-l-4 border-blue-400'
            );
            container.appendChild(promptSection);
        }

        // Response section
        if (llmCall.response) {
            const responseSection = this._createExpandableSection(
                'Response', 
                llmCall.response,
                'bg-green-50 border-l-4 border-green-400'
            );
            container.appendChild(responseSection);
        }

        return container;
    }

    /**
     * Create an expandable section for prompt/response
     * @param {string} title - Section title
     * @param {string} content - Section content
     * @param {string} containerClass - Additional CSS classes for container
     * @returns {HTMLElement} Expandable section element
     */
    _createExpandableSection(title, content, containerClass = '') {
        const section = document.createElement('div');
        section.className = `llm-section mb-3 ${containerClass} rounded`;

        const header = document.createElement('div');
        header.className = 'cursor-pointer p-3 hover:bg-opacity-80 select-none';
        
        const headerContent = document.createElement('div');
        headerContent.className = 'flex justify-between items-center';
        
        const titleEl = document.createElement('span');
        titleEl.className = 'font-medium text-sm';
        titleEl.textContent = title;
        
        const toggle = document.createElement('span');
        toggle.className = 'text-gray-500 text-xs';
        toggle.textContent = 'Click to expand';
        
        headerContent.appendChild(titleEl);
        headerContent.appendChild(toggle);
        header.appendChild(headerContent);

        const contentEl = document.createElement('div');
        contentEl.className = 'llm-content hidden px-3 pb-3';
        
        const pre = document.createElement('pre');
        pre.className = 'text-sm bg-white p-3 rounded border overflow-auto max-h-96 whitespace-pre-wrap';
        pre.textContent = content;
        
        contentEl.appendChild(pre);

        // Toggle functionality
        const toggleContent = () => {
            const isHidden = contentEl.classList.contains('hidden');
            if (isHidden) {
                contentEl.classList.remove('hidden');
                toggle.textContent = 'Click to collapse';
            } else {
                contentEl.classList.add('hidden');
                toggle.textContent = 'Click to expand';
            }
        };

        header.addEventListener('click', toggleContent);

        section.appendChild(header);
        section.appendChild(contentEl);

        return section;
    }

    /**
     * Create a "no data" placeholder element
     * @param {string} message - Message to display
     * @returns {HTMLElement} No data element
     */
    _createNoDataElement(message) {
        const el = document.createElement('div');
        el.className = 'text-sm text-gray-500 italic p-3 bg-gray-50 rounded border';
        el.textContent = message;
        return el;
    }
}

// Export for use in other scripts
if (typeof window !== 'undefined') {
    window.LLMCallComponent = LLMCallComponent;
}

// Also export for module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = LLMCallComponent;
}
