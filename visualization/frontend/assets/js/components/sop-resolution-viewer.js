/**
 * SOP Resolution Viewer component for Doc Flow Trace Viewer
 * Dedicated component for displaying SOP resolution phase details
 */

class SOPResolutionViewer {
    constructor() {
        this.llmCallComponent = new LLMCallComponent();
    }

    /**
     * Create SOP resolution phase display element
     * @param {Object} sopResolutionData - SOP resolution phase data
     * @returns {HTMLElement} SOP resolution element
     */
    createSOPResolutionElement(sopResolutionData) {
        if (!sopResolutionData) {
            return this._createNoDataElement('No SOP resolution data available');
        }

        const container = document.createElement('div');
        container.className = 'sop-resolution-container';

        // Create collapsed summary
        const summary = this._createCollapsedSummary(sopResolutionData);
        container.appendChild(summary);

        // Create expandable detailed view
        const details = this._createExpandedDetails(sopResolutionData);
        container.appendChild(details);

        return container;
    }

    /**
     * Create collapsed summary view
     * @param {Object} data - SOP resolution data
     * @returns {HTMLElement} Summary element
     */
    _createCollapsedSummary(data) {
        const summary = document.createElement('div');
        summary.className = 'sop-summary p-3 bg-gray-50 border rounded mb-3';

        // Selected document info
        const selectedDoc = document.createElement('div');
        selectedDoc.className = 'mb-2';

        if (data.selected_doc_id) {
            selectedDoc.innerHTML = `<strong>Selected Document:</strong> ${FormattingUtils.escapeHtml(data.selected_doc_id)}`;
            
            // Add description if available
            if (data.loaded_sop_document?.description) {
                const desc = document.createElement('div');
                desc.className = 'text-sm text-gray-600 mt-1';
                desc.textContent = data.loaded_sop_document.description;
                selectedDoc.appendChild(desc);
            }
        } else {
            selectedDoc.innerHTML = '<strong>Selected Document:</strong> <span class="text-red-600">None selected</span>';
        }

        summary.appendChild(selectedDoc);

        // Candidate count and selection method
        const candidateInfo = this._createCandidateInfo(data);
        summary.appendChild(candidateInfo);

        // Selection method badge
        const methodBadge = this._createSelectionMethodBadge(data);
        summary.appendChild(methodBadge);

        return summary;
    }

    /**
     * Create candidate documents information
     * @param {Object} data - SOP resolution data
     * @returns {HTMLElement} Candidate info element
     */
    _createCandidateInfo(data) {
        const info = document.createElement('div');
        info.className = 'text-sm mb-2';

        const candidateCount = data.candidate_documents?.length || 0;
        const hasLLMValidation = !!data.llm_validation_call;

        let statusText = '';
        let statusClass = '';

        if (candidateCount === 0) {
            statusText = 'No candidates found (fallback used)';
            statusClass = 'text-orange-600';
        } else if (candidateCount === 1 && data.selected_doc_id === data.candidate_documents[0]) {
            statusText = `Perfect match (1 candidate)`;
            statusClass = 'text-green-600';
        } else if (candidateCount > 1) {
            if (hasLLMValidation) {
                const llmResponse = data.llm_validation_call.response || '';
                if (llmResponse.includes('NONE')) {
                    statusText = `Alert: LLM rejected ${candidateCount} candidates`;
                    statusClass = 'text-red-600 font-semibold';
                } else {
                    statusText = `LLM selected from ${candidateCount} candidates`;
                    statusClass = 'text-blue-600';
                }
            } else {
                statusText = `${candidateCount} candidates found`;
                statusClass = 'text-gray-600';
            }
        } else {
            statusText = `${candidateCount} candidates`;
            statusClass = 'text-gray-600';
        }

        info.innerHTML = `<strong>Selection Status:</strong> <span class="${statusClass}">${statusText}</span>`;
        return info;
    }

    /**
     * Create selection method badge
     * @param {Object} data - SOP resolution data
     * @returns {HTMLElement} Method badge element
     */
    _createSelectionMethodBadge(data) {
        const badgeContainer = document.createElement('div');
        badgeContainer.className = 'flex gap-2 flex-wrap';

        // Determine selection methods from candidate documents
        const candidateDocs = data.candidate_documents || [];
        const matchTypes = new Set();

        // Extract match types from LLM validation prompt if available
        if (data.llm_validation_call?.prompt) {
            const prompt = data.llm_validation_call.prompt;
            if (prompt.includes('match_type: full_path')) matchTypes.add('full_path');
            if (prompt.includes('match_type: filename')) matchTypes.add('filename');
            if (prompt.includes('match_type: alias')) matchTypes.add('alias');
        }

        // Create badges for each match type
        matchTypes.forEach(type => {
            const badge = this._createMethodBadge(type);
            badgeContainer.appendChild(badge);
        });

        // If no match types found, show fallback badge
        if (matchTypes.size === 0 && candidateDocs.length === 0) {
            const badge = this._createMethodBadge('fallback');
            badgeContainer.appendChild(badge);
        }

        return badgeContainer;
    }

    /**
     * Create a single method badge
     * @param {string} method - Selection method
     * @returns {HTMLElement} Badge element
     */
    _createMethodBadge(method) {
        const badge = document.createElement('span');
        badge.className = 'inline-block px-2 py-1 text-xs font-medium rounded';
        badge.textContent = method.replace('_', ' ').toUpperCase();

        // Color coding based on method
        switch (method) {
            case 'full_path':
                badge.className += ' bg-green-100 text-green-800';
                break;
            case 'filename':
                badge.className += ' bg-blue-100 text-blue-800';
                break;
            case 'alias':
                badge.className += ' bg-purple-100 text-purple-800';
                break;
            case 'fallback':
                badge.className += ' bg-orange-100 text-orange-800';
                break;
            default:
                badge.className += ' bg-gray-100 text-gray-800';
        }

        return badge;
    }

    /**
     * Create expanded detailed view
     * @param {Object} data - SOP resolution data
     * @returns {HTMLElement} Details element
     */
    _createExpandedDetails(data) {
        const details = document.createElement('details');
        details.className = 'mt-2';
        
        const summary = document.createElement('summary');
        summary.className = 'cursor-pointer text-sm text-blue-700 font-semibold';
        summary.textContent = 'View SOP Resolution Details';
        details.appendChild(summary);
        
        const contentContainer = document.createElement('div');
        contentContainer.className = 'mt-2 p-4 bg-gray-50 rounded space-y-4';

        // Candidate Documents Section
        if (data.candidate_documents?.length > 0) {
            const candidatesSection = this._createCandidatesSection(data.candidate_documents, data.llm_validation_call);
            contentContainer.appendChild(candidatesSection);
        }

        // LLM Validation Section
        if (data.llm_validation_call) {
            const llmSection = this.llmCallComponent.createLLMCallElement(
                data.llm_validation_call, 
                'SOP Document Validation'
            );
            contentContainer.appendChild(llmSection);
        }

        // Selected Document Details
        if (data.loaded_sop_document) {
            const docSection = this._createSelectedDocumentSection(data.loaded_sop_document);
            contentContainer.appendChild(docSection);
        }

        // Error information
        if (data.error) {
            const errorSection = this._createErrorSection(data.error);
            contentContainer.appendChild(errorSection);
        }

        details.appendChild(contentContainer);
        return details;
    }

    /**
     * Create candidate documents section
     * @param {Array} candidates - Candidate documents
     * @param {Object} llmCall - LLM validation call data
     * @returns {HTMLElement} Candidates section element
     */
    _createCandidatesSection(candidates, llmCall) {
        const section = document.createElement('div');
        section.className = 'candidates-section bg-blue-50 border border-blue-200 rounded p-4';

        const header = document.createElement('h4');
        header.className = 'text-md font-semibold text-blue-800 mb-3';
        header.textContent = `Candidate Documents (${candidates.length})`;

        section.appendChild(header);

        // Parse match types from LLM prompt if available
        const matchTypeMap = this._parseMatchTypesFromLLMPrompt(llmCall);

        candidates.forEach((candidate, index) => {
            const candidateEl = document.createElement('div');
            candidateEl.className = 'candidate-item p-3 mb-2 bg-white border rounded';

            const candidateHeader = document.createElement('div');
            candidateHeader.className = 'flex justify-between items-start';

            const candidateInfo = document.createElement('div');
            candidateInfo.innerHTML = `<strong>${index + 1}. ${FormattingUtils.escapeHtml(candidate)}</strong>`;

            // Add match type badge if available
            const matchType = matchTypeMap[candidate];
            if (matchType) {
                const badge = this._createMethodBadge(matchType);
                badge.className += ' ml-2';
                candidateInfo.appendChild(badge);
            }

            candidateHeader.appendChild(candidateInfo);
            candidateEl.appendChild(candidateHeader);

            // Add description if available from LLM prompt
            const description = this._extractDescriptionFromLLMPrompt(candidate, llmCall);
            if (description) {
                const descEl = document.createElement('div');
                descEl.className = 'text-sm text-gray-600 mt-1';
                descEl.textContent = description;
                candidateEl.appendChild(descEl);
            }

            section.appendChild(candidateEl);
        });

        return section;
    }

    /**
     * Parse match types from LLM validation prompt
     * @param {Object} llmCall - LLM call data
     * @returns {Object} Map of candidate to match type
     */
    _parseMatchTypesFromLLMPrompt(llmCall) {
        const matchTypeMap = {};
        
        if (!llmCall?.prompt) return matchTypeMap;

        const prompt = llmCall.prompt;
        const lines = prompt.split('\n');

        let currentCandidate = null;
        for (const line of lines) {
            // Look for doc_id lines
            const docMatch = line.match(/doc_id: (.+)$/);
            if (docMatch) {
                currentCandidate = docMatch[1].trim();
            }
            
            // Look for match_type lines
            const matchTypeMatch = line.match(/match_type: (.+)$/);
            if (matchTypeMatch && currentCandidate) {
                matchTypeMap[currentCandidate] = matchTypeMatch[1].trim();
                currentCandidate = null; // Reset for next candidate
            }
        }

        return matchTypeMap;
    }

    /**
     * Extract description for a candidate from LLM prompt
     * @param {string} candidate - Candidate document ID
     * @param {Object} llmCall - LLM call data
     * @returns {string|null} Description if found
     */
    _extractDescriptionFromLLMPrompt(candidate, llmCall) {
        if (!llmCall?.prompt) return null;

        const prompt = llmCall.prompt;
        const lines = prompt.split('\n');

        for (let i = 0; i < lines.length; i++) {
            const line = lines[i];
            if (line.includes(`doc_id: ${candidate}`)) {
                // Look for description in next few lines
                for (let j = i + 1; j < Math.min(i + 4, lines.length); j++) {
                    const nextLine = lines[j];
                    const descMatch = nextLine.match(/description: (.+)$/);
                    if (descMatch) {
                        return descMatch[1].trim();
                    }
                }
            }
        }

        return null;
    }

    /**
     * Create selected document details section
     * @param {Object} doc - Loaded SOP document
     * @returns {HTMLElement} Document section element
     */
    _createSelectedDocumentSection(doc) {
        const section = document.createElement('div');
        section.className = 'selected-doc-section bg-green-50 border border-green-200 rounded p-4';

        const header = document.createElement('h4');
        header.className = 'text-md font-semibold text-green-800 mb-3';
        header.textContent = 'Selected Document Details';

        section.appendChild(header);

        // Basic document info
        const basicInfo = document.createElement('div');
        basicInfo.className = 'mb-4';

        const docId = document.createElement('div');
        docId.innerHTML = `<strong>Document ID:</strong> ${FormattingUtils.escapeHtml(doc.doc_id || '')}`;

        const description = document.createElement('div');
        description.innerHTML = `<strong>Description:</strong> ${FormattingUtils.escapeHtml(doc.description || '')}`;

        basicInfo.appendChild(docId);
        basicInfo.appendChild(description);

        if (doc.aliases?.length > 0) {
            const aliases = document.createElement('div');
            aliases.innerHTML = `<strong>Aliases:</strong> ${doc.aliases.map(a => FormattingUtils.escapeHtml(a)).join(', ')}`;
            basicInfo.appendChild(aliases);
        }

        section.appendChild(basicInfo);

        // Tool configuration
        if (doc.tool) {
            const toolSection = this._createSubSection('Tool Configuration', doc.tool);
            section.appendChild(toolSection);
        }

        // Input/Output paths
        if (doc.input_json_path && Object.keys(doc.input_json_path).length > 0) {
            const inputSection = this._createSubSection('Input JSON Paths', doc.input_json_path);
            section.appendChild(inputSection);
        }

        if (doc.output_json_path) {
            const outputSection = this._createSubSection('Output JSON Path', doc.output_json_path);
            section.appendChild(outputSection);
        }

        // Parameters
        if (doc.parameters && Object.keys(doc.parameters).length > 0) {
            const paramsSection = this._createSubSection('Parameters', doc.parameters);
            section.appendChild(paramsSection);
        }

        return section;
    }

    /**
     * Create a subsection with expandable JSON content
     * @param {string} title - Section title
     * @param {Object} data - Data to display
     * @returns {HTMLElement} Subsection element
     */
    _createSubSection(title, data) {
        const subsection = document.createElement('div');
        subsection.className = 'mb-3';

        const subheader = document.createElement('h5');
        subheader.className = 'text-sm font-medium text-gray-700 mb-2';
        subheader.textContent = title;

        const content = document.createElement('div');
        content.className = 'bg-white border rounded p-3';

        const pre = document.createElement('pre');
        pre.className = 'text-sm text-gray-800 overflow-auto max-h-48 whitespace-pre-wrap';
        pre.textContent = JSON.stringify(data, null, 2);

        content.appendChild(pre);
        subsection.appendChild(subheader);
        subsection.appendChild(content);

        return subsection;
    }

    /**
     * Create error section
     * @param {string} error - Error message
     * @returns {HTMLElement} Error section element
     */
    _createErrorSection(error) {
        const section = document.createElement('div');
        section.className = 'error-section bg-red-50 border border-red-200 rounded p-4';

        const header = document.createElement('h4');
        header.className = 'text-md font-semibold text-red-800 mb-2';
        header.textContent = 'Error';

        const errorMsg = document.createElement('div');
        errorMsg.className = 'text-sm text-red-700';
        errorMsg.textContent = error;

        section.appendChild(header);
        section.appendChild(errorMsg);

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
    window.SOPResolutionViewer = SOPResolutionViewer;
}

// Also export for module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = SOPResolutionViewer;
}
