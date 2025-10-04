import React, { useState, useCallback } from 'react';
import type { SOPResolutionPhase } from '../../types/trace';
import { ContextualLLMCall } from '../enhanced/ContextualLLMCall';
import { sopDocsService } from '../../services';
import '../SOPDocs/SopModalShared.css';

interface SOPResolutionViewerProps {
  phaseData: SOPResolutionPhase;
}

export const SOPResolutionViewer: React.FC<SOPResolutionViewerProps> = ({ phaseData }) => {
  const documentSelection = phaseData.document_selection;
  const [rawModal, setRawModal] = useState<{open: boolean; loading: boolean; content: string; docPath?: string}>({open:false, loading:false, content:''});

  const openRawDoc = useCallback((docId: string | null | undefined) => {
    if (!docId) return;
    setRawModal({ open: true, loading: true, content: 'Loading...', docPath: docId });
    sopDocsService.getRaw(docId)
      .then(r => {
        if (r?.content) {
          setRawModal({ open: true, loading: false, content: r.content, docPath: docId });
        } else {
          setRawModal({ open: true, loading: false, content: 'Failed to load document', docPath: docId });
        }
      })
      .catch(() => setRawModal({ open: true, loading: false, content: 'Error loading document', docPath: docId }));
  }, []);
  // NOTE: We provide an "open in new tab" icon for each candidate and the loaded SOP document.
  // This currently constructs the URL as /sop-docs/<docId>. If in the future doc_id differs
  // from the document path, introduce a resolver (e.g., map doc_id -> path) and update links.
  // Graceful fallback: if no docId we render a disabled icon placeholder with tooltip.
  
  return (
    <div className="space-y-4">
      {/* Input Description */}
      {phaseData.input?.description && (
        <div>
          <h4 className="text-sm font-medium text-gray-700 mb-2">Input Description</h4>
          <div className="bg-gray-50 border rounded p-3">
            <p className="text-sm text-gray-700">{phaseData.input.description}</p>
          </div>
        </div>
      )}

      {/* Document Selection Sub-step */}
      {documentSelection && (
        <div className="border border-blue-200 rounded-lg">
          <div className="px-3 py-2 bg-blue-50 border-b border-blue-200 rounded-t-lg">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-blue-900">Document Selection</span>
              <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                documentSelection.status === 'completed' ? 'bg-green-100 text-green-800' : 
                documentSelection.status === 'failed' ? 'bg-red-100 text-red-800' : 
                'bg-blue-100 text-blue-800'
              }`}>
                {documentSelection.status}
              </span>
            </div>
          </div>
          <div className="p-3 space-y-4">
            
            {/* Candidate Documents */}
            {documentSelection.candidate_documents && documentSelection.candidate_documents.length > 0 && (
              <div>
                <h5 className="text-sm font-medium text-gray-700 mb-2">
                  Candidate Documents ({documentSelection.candidate_documents.length})
                </h5>
                <div className="space-y-2">
                  {documentSelection.candidate_documents.map((docId, index) => {
                    const docUrl = docId ? `/sop-docs/${docId}` : null;
                    return (
                      <div 
                        key={index}
                        className={`p-3 rounded border flex items-start justify-between gap-3 ${
                          docId === documentSelection.selected_doc_id 
                            ? 'bg-green-50 border-green-200' 
                            : 'bg-gray-50 border-gray-200'
                        }`}
                        onClick={() => openRawDoc(docId)}
                        style={{ cursor: docId ? 'pointer' : 'default' }}
                      >
                        <div className="flex-1 min-w-0">
                          <span className="font-mono text-sm break-all">{docId}</span>
                          {docId === documentSelection.selected_doc_id && (
                            <span className="ml-2 inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                              Selected
                            </span>
                          )}
                        </div>
                        {docUrl ? (
                          <a
                            href={docUrl}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-gray-500 hover:text-blue-600 transition-colors"
                            title="Open SOP document in new tab"
                            aria-label={`Open SOP document ${docId} in new tab`}
                            onClick={(e) => { e.stopPropagation(); }}
                          >
                            <svg
                              xmlns="http://www.w3.org/2000/svg"
                              viewBox="0 0 20 20"
                              fill="currentColor"
                              className="h-4 w-4"
                            >
                              <path d="M11 3a1 1 0 100 2h2.586l-6.293 6.293a1 1 0 101.414 1.414L15 6.414V9a1 1 0 102 0V4a1 1 0 00-1-1h-5z" />
                              <path d="M5 5a2 2 0 00-2 2v8a2 2 0 002 2h8a2 2 0 002-2v-3a1 1 0 10-2 0v3H5V7h3a1 1 0 000-2H5z" />
                            </svg>
                          </a>
                        ) : (
                          <span
                            className="text-gray-300"
                            title="Document ID unavailable for linking"
                            aria-hidden="true"
                          >
                            <svg
                              xmlns="http://www.w3.org/2000/svg"
                              viewBox="0 0 20 20"
                              fill="currentColor"
                              className="h-4 w-4"
                            >
                              <path d="M11 3a1 1 0 100 2h2.586l-6.293 6.293a1 1 0 101.414 1.414L15 6.414V9a1 1 0 102 0V4a1 1 0 00-1-1h-5z" />
                              <path d="M5 5a2 2 0 00-2 2v8a2 2 0 002 2h8a2 2 0 002-2v-3a1 1 0 10-2 0v3H5V7h3a1 1 0 000-2H5z" />
                            </svg>
                          </span>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Selected Document Details */}
            {documentSelection.loaded_document && (
              <div>
                <div className="flex items-center justify-between mb-2">
                  <h5 className="text-sm font-medium text-gray-700">Selected SOP Document</h5>
                  {documentSelection.loaded_document.doc_id && (
                    <a
                      href={`/sop-docs/${documentSelection.loaded_document.doc_id}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-gray-500 hover:text-blue-600 transition-colors flex items-center gap-1"
                      title="Open selected SOP document in new tab"
                      aria-label={`Open SOP document ${documentSelection.loaded_document.doc_id} in new tab`}
                    >
                      <svg
                        xmlns="http://www.w3.org/2000/svg"
                        viewBox="0 0 20 20"
                        fill="currentColor"
                        className="h-4 w-4"
                      >
                        <path d="M11 3a1 1 0 100 2h2.586l-6.293 6.293a1 1 0 101.414 1.414L15 6.414V9a1 1 0 102 0V4a1 1 0 00-1-1h-5z" />
                        <path d="M5 5a2 2 0 00-2 2v8a2 2 0 002 2h8a2 2 0 002-2v-3a1 1 0 10-2 0v3H5V7h3a1 1 0 000-2H5z" />
                      </svg>
                    </a>
                  )}
                </div>
                <div 
                  className="bg-blue-50 border border-blue-200 rounded p-4 cursor-pointer"
                  onClick={() => openRawDoc(documentSelection.loaded_document?.doc_id)}
                  title="Click to view full raw document"
                >
                  <pre className="text-xs text-gray-700 overflow-x-auto">
{JSON.stringify(documentSelection.loaded_document, null, 2)}
                  </pre>
                </div>
              </div>
            )}

            {/* LLM Validation Calls */}
            {documentSelection.llm_calls && documentSelection.llm_calls.length > 0 && (
              <div>
                <div className="border border-purple-200 rounded-lg">
                  <div className="px-3 py-2 bg-purple-50 border-b border-purple-200 rounded-t-lg">
                    <span className="text-sm font-medium text-purple-900">Document Selection LLM Calls ({documentSelection.llm_calls.length})</span>
                  </div>
                  <div className="p-3 space-y-3">
                    {documentSelection.llm_calls.map((call, idx) => (
                      <ContextualLLMCall 
                        key={call.tool_call_id || idx}
                        llmCall={call}
                        context="sop_validation"
                        relatedData={{ 
                          candidateDocuments: documentSelection.candidate_documents,
                          selectedDocument: documentSelection.selected_doc_id,
                          inputDescription: phaseData.input?.description
                        }}
                      />
                    ))}
                  </div>
                </div>
              </div>
            )}
            {/* Backward compatibility: single validation_call */}
            {!documentSelection.llm_calls && (documentSelection as any).validation_call && (
              <div>
                <div className="border border-purple-200 rounded-lg">
                  <div className="px-3 py-2 bg-purple-50 border-b border-purple-200 rounded-t-lg">
                    <span className="text-sm font-medium text-purple-900">Document Selection Validation</span>
                  </div>
                  <div className="p-3">
                    <ContextualLLMCall 
                      llmCall={(documentSelection as any).validation_call}
                      context="sop_validation"
                      relatedData={{ 
                        candidateDocuments: documentSelection.candidate_documents,
                        selectedDocument: documentSelection.selected_doc_id,
                        inputDescription: phaseData.input?.description
                      }}
                    />
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Error */}
      {phaseData.error && (
        <div>
          <h4 className="text-sm font-medium text-red-700 mb-2">Error</h4>
          <div className="bg-red-50 border border-red-200 rounded p-3">
            <p className="text-sm text-red-700 font-mono whitespace-pre-wrap">
              {phaseData.error}
            </p>
          </div>
        </div>
      )}

      {rawModal.open && (
        <div className="sop-ref-modal-overlay" onClick={(e) => { if (e.target === e.currentTarget) setRawModal(m=>({...m, open:false})); }}>
          <div className="sop-ref-modal" role="dialog" aria-modal="true">
            <div className="sop-ref-modal-header">
              <span>{rawModal.docPath}</span>
              <button className="sop-ref-modal-close" onClick={() => setRawModal(m=>({...m, open:false}))}>✕</button>
            </div>
            <div className="sop-ref-modal-body">
              <pre><code>{rawModal.content}</code></pre>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
