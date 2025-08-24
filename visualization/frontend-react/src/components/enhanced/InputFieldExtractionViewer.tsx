import React, { useState } from 'react';
import type { InputFieldExtraction } from '../../types/trace';
import { ContextualLLMCall } from './ContextualLLMCall';

interface InputFieldExtractionViewerProps {
  fieldName: string;
  description: string;
  fieldExtraction: InputFieldExtraction;
}

interface CollapsibleSectionProps {
  title: string;
  children: React.ReactNode;
  defaultExpanded?: boolean;
  variant?: 'default' | 'success' | 'error' | 'info';
}

const CollapsibleSection: React.FC<CollapsibleSectionProps> = ({ 
  title, 
  children, 
  defaultExpanded = false,
  variant = 'default'
}) => {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);

  const getVariantStyles = () => {
    switch (variant) {
      case 'success':
        return 'border-green-200 bg-green-50 hover:bg-green-100';
      case 'error':
        return 'border-red-200 bg-red-50 hover:bg-red-100';
      case 'info':
        return 'border-blue-200 bg-blue-50 hover:bg-blue-100';
      default:
        return 'border-gray-200 bg-gray-50 hover:bg-gray-100';
    }
  };

  return (
    <div className="border rounded-md">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className={`w-full px-3 py-2 text-left focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-inset transition-colors border-b border-gray-200 rounded-t-md text-sm ${getVariantStyles()}`}
      >
        <div className="flex items-center justify-between">
          <span className="font-medium text-gray-900">{title}</span>
          <svg
            className={`h-4 w-4 text-gray-500 transition-transform ${isExpanded ? 'rotate-180' : ''}`}
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </div>
      </button>
      
      {isExpanded && (
        <div className="p-3 border-t border-gray-200">
          {children}
        </div>
      )}
    </div>
  );
};

export const InputFieldExtractionViewer: React.FC<InputFieldExtractionViewerProps> = ({
  fieldName,
  description,
  fieldExtraction
}) => {
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'bg-green-100 text-green-800';
      case 'failed':
        return 'bg-red-100 text-red-800';
      case 'started':
        return 'bg-blue-100 text-blue-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const formatTime = (timestamp: string | null): string => {
    if (!timestamp) return 'N/A';
    try {
      return new Date(timestamp).toLocaleString();
    } catch (error) {
      return 'Invalid time';
    }
  };

  const calculateDuration = (startTime: string, endTime: string | null): string => {
    if (!startTime || !endTime) return 'N/A';
    
    try {
      const start = new Date(startTime);
      const end = new Date(endTime);
      const diffMs = end.getTime() - start.getTime();
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
  };

  return (
    <div className="bg-white border rounded-lg shadow-sm">
      {/* Header */}
      <div className="px-4 py-3 border-b bg-gray-50 rounded-t-lg">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="font-mono font-medium text-gray-900">{fieldName}</span>
            <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getStatusColor(fieldExtraction.status)}`}>
              {fieldExtraction.status}
            </span>
          </div>
          <div className="text-sm text-gray-500">
            {formatTime(fieldExtraction.start_time)} - {formatTime(fieldExtraction.end_time)} 
            ({calculateDuration(fieldExtraction.start_time, fieldExtraction.end_time)})
          </div>
        </div>
        {description && (
          <p className="mt-2 text-sm text-gray-600">{description}</p>
        )}
      </div>

      <div className="p-4 space-y-4">
        {/* Error */}
        {fieldExtraction.error && (
          <div className="bg-red-50 border border-red-200 rounded p-3">
            <div className="flex items-start gap-2">
              <svg className="h-5 w-5 text-red-500 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <div>
                <h5 className="font-medium text-red-900">Extraction Error</h5>
                <p className="text-sm text-red-700 mt-1">{fieldExtraction.error}</p>
              </div>
            </div>
          </div>
        )}

        {/* Results Summary */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="text-sm font-medium text-gray-700">Extracted Value</label>
            <div className="mt-1 p-3 bg-blue-50 border border-blue-200 rounded text-sm">
              {fieldExtraction.extracted_value !== null ? (
                <span className="font-mono">{JSON.stringify(fieldExtraction.extracted_value, null, 2)}</span>
              ) : (
                <span className="text-gray-500">No value extracted</span>
              )}
            </div>
          </div>
          <div>
            <label className="text-sm font-medium text-gray-700">Generated Path</label>
            <div className="mt-1 p-3 bg-green-50 border border-green-200 rounded text-sm">
              {fieldExtraction.generated_path ? (
                <span className="font-mono">{fieldExtraction.generated_path}</span>
              ) : (
                <span className="text-gray-500">No path generated</span>
              )}
            </div>
          </div>
        </div>

        {/* Candidate Fields */}
        {fieldExtraction.candidate_fields && Object.keys(fieldExtraction.candidate_fields).length > 0 && (
          <CollapsibleSection title={`Candidate Fields (${Object.keys(fieldExtraction.candidate_fields).length})`} variant="info">
            <div className="space-y-2">
              {Object.entries(fieldExtraction.candidate_fields).map(([key, value]) => (
                <div key={key} className="flex items-start gap-3 p-2 bg-gray-50 rounded">
                  <span className="font-mono text-sm font-medium text-blue-600">{key}:</span>
                  <span className="font-mono text-sm text-gray-700 flex-1 min-w-0 break-all">
                    {typeof value === 'string' ? value : JSON.stringify(value)}
                  </span>
                </div>
              ))}
            </div>
          </CollapsibleSection>
        )}

        {/* Generated Extraction Code */}
        {fieldExtraction.generated_extraction_code && (
          <CollapsibleSection title="Generated Extraction Code" variant="info">
            <pre className="text-xs text-gray-700 bg-gray-50 p-3 rounded border overflow-x-auto">
              {fieldExtraction.generated_extraction_code}
            </pre>
          </CollapsibleSection>
        )}

        {/* LLM Calls */}
        <div className="space-y-3">
          {/* Context Analysis Call */}
          {fieldExtraction.context_analysis_call && (
            <div className="border border-purple-200 rounded-lg">
              <div className="px-3 py-2 bg-purple-50 border-b border-purple-200 rounded-t-lg">
                <span className="text-sm font-medium text-purple-900">Context Analysis</span>
              </div>
              <div className="p-3">
                <ContextualLLMCall 
                  llmCall={fieldExtraction.context_analysis_call}
                  context="field_extraction"
                  relatedData={{ 
                    fieldName,
                    description,
                    candidateFields: fieldExtraction.candidate_fields
                  }}
                />
              </div>
            </div>
          )}

          {/* Extraction Code Generation Call */}
          {fieldExtraction.extraction_code_generation_call && (
            <div className="border border-indigo-200 rounded-lg">
              <div className="px-3 py-2 bg-indigo-50 border-b border-indigo-200 rounded-t-lg">
                <span className="text-sm font-medium text-indigo-900">Code Generation</span>
              </div>
              <div className="p-3">
                <ContextualLLMCall 
                  llmCall={fieldExtraction.extraction_code_generation_call}
                  context="field_extraction"
                  relatedData={{ 
                    fieldName,
                    description,
                    generatedCode: fieldExtraction.generated_extraction_code,
                    extractedValue: fieldExtraction.extracted_value
                  }}
                />
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
