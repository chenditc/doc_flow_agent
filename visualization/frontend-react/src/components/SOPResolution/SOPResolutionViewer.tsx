import React from 'react';
import type { SOPResolutionPhase } from '../../types/trace';

interface SOPResolutionViewerProps {
  phaseData: SOPResolutionPhase;
}

export const SOPResolutionViewer: React.FC<SOPResolutionViewerProps> = ({ phaseData }) => {
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

      {/* Candidate Documents */}
      {phaseData.candidate_documents && phaseData.candidate_documents.length > 0 && (
        <div>
          <h4 className="text-sm font-medium text-gray-700 mb-2">
            Candidate Documents ({phaseData.candidate_documents.length})
          </h4>
          <div className="space-y-2">
            {phaseData.candidate_documents.map((docId, index) => (
              <div 
                key={index}
                className={`p-3 rounded border ${
                  docId === phaseData.selected_doc_id 
                    ? 'bg-green-50 border-green-200' 
                    : 'bg-gray-50 border-gray-200'
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="font-mono text-sm">{docId}</span>
                  {docId === phaseData.selected_doc_id && (
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
      {phaseData.loaded_sop_document && (
        <div>
          <h4 className="text-sm font-medium text-gray-700 mb-2">Selected SOP Document</h4>
          <div className="bg-blue-50 border border-blue-200 rounded p-4">
            <div className="grid grid-cols-1 gap-3">
              <div>
                <span className="text-sm font-medium text-blue-900">ID:</span>
                <span className="ml-2 font-mono text-sm text-blue-800">{phaseData.loaded_sop_document.doc_id}</span>
              </div>
              <div>
                <span className="text-sm font-medium text-blue-900">Description:</span>
                <span className="ml-2 text-sm text-blue-800">{phaseData.loaded_sop_document.description}</span>
              </div>
              {phaseData.loaded_sop_document.aliases?.length > 0 && (
                <div>
                  <span className="text-sm font-medium text-blue-900">Aliases:</span>
                  <div className="ml-2 flex flex-wrap gap-1 mt-1">
                    {phaseData.loaded_sop_document.aliases.map((alias, index) => (
                      <span key={index} className="inline-flex items-center px-2 py-0.5 rounded text-xs bg-blue-100 text-blue-800">
                        {alias}
                      </span>
                    ))}
                  </div>
                </div>
              )}
              <div>
                <span className="text-sm font-medium text-blue-900">Tool ID:</span>
                <span className="ml-2 font-mono text-sm text-blue-800">{phaseData.loaded_sop_document.tool.tool_id}</span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* LLM Validation Call */}
      {phaseData.llm_validation_call && (
        <div>
          <h4 className="text-sm font-medium text-gray-700 mb-2">LLM Validation</h4>
          <div className="bg-purple-50 border border-purple-200 rounded p-3">
            <div className="text-sm text-purple-800">
              LLM validation call made - details available in LLM Call component
            </div>
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
