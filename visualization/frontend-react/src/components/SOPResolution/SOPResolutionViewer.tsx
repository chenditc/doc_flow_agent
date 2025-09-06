import React from 'react';
import type { SOPResolutionPhase } from '../../types/trace';
import { ContextualLLMCall } from '../enhanced/ContextualLLMCall';

interface SOPResolutionViewerProps {
  phaseData: SOPResolutionPhase;
}

export const SOPResolutionViewer: React.FC<SOPResolutionViewerProps> = ({ phaseData }) => {
  const documentSelection = phaseData.document_selection;
  
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
                  {documentSelection.candidate_documents.map((docId, index) => (
                    <div 
                      key={index}
                      className={`p-3 rounded border ${
                        docId === documentSelection.selected_doc_id 
                          ? 'bg-green-50 border-green-200' 
                          : 'bg-gray-50 border-gray-200'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-mono text-sm">{docId}</span>
                        {docId === documentSelection.selected_doc_id && (
                          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                            Selected
                          </span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Selected Document Details */}
            {documentSelection.loaded_document && (
              <div>
                <h5 className="text-sm font-medium text-gray-700 mb-2">Selected SOP Document</h5>
                <div className="bg-blue-50 border border-blue-200 rounded p-4">
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
    </div>
  );
};
