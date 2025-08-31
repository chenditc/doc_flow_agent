import React, { useState } from 'react';
import type { BatchInputFieldExtraction } from '../../types/trace';
import { ContextualLLMCall } from './ContextualLLMCall';
import { InfoIconWithTooltip } from '../common/Tooltip';

interface BatchInputFieldExtractionViewerProps {
  batchExtraction: BatchInputFieldExtraction;
}

export const BatchInputFieldExtractionViewer: React.FC<BatchInputFieldExtractionViewerProps> = ({ 
  batchExtraction 
}) => {
  const [expandedSections, setExpandedSections] = useState<Set<string>>(new Set(['overview']));

  const toggleSection = (sectionId: string) => {
    const newExpanded = new Set(expandedSections);
    if (newExpanded.has(sectionId)) {
      newExpanded.delete(sectionId);
    } else {
      newExpanded.add(sectionId);
    }
    setExpandedSections(newExpanded);
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
    } catch {
      return 'Invalid duration';
    }
  };

  const getStatusColor = (status: string): string => {
    switch (status) {
      case 'completed':
        return 'text-green-700 bg-green-50 border-green-200';
      case 'failed':
        return 'text-red-700 bg-red-50 border-red-200';
      case 'started':
        return 'text-blue-700 bg-blue-50 border-blue-200';
      default:
        return 'text-gray-700 bg-gray-50 border-gray-200';
    }
  };

  const CollapsibleSection: React.FC<{
    title: string;
    sectionId: string;
    children: React.ReactNode;
    defaultExpanded?: boolean;
    badge?: React.ReactNode;
  }> = ({ title, sectionId, children, badge }) => {
    const isExpanded = expandedSections.has(sectionId);
    
    return (
      <div className="border rounded-lg">
        <button
          onClick={() => toggleSection(sectionId)}
          className="w-full px-4 py-3 text-left bg-gray-50 hover:bg-gray-100 focus:outline-none focus:bg-gray-100 transition-colors border-b border-gray-200 rounded-t-lg"
        >
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <span className="font-medium text-gray-900">{title}</span>
              {badge}
            </div>
            <svg
              className={`h-5 w-5 text-gray-500 transition-transform ${isExpanded ? 'rotate-180' : ''}`}
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          </div>
        </button>
        
        {isExpanded && (
          <div className="p-4">
            {children}
          </div>
        )}
      </div>
    );
  };

  const fieldCount = Object.keys(batchExtraction.input_descriptions || {}).length;
  const extractedCount = Object.keys(batchExtraction.extracted_values || {}).length;

  return (
    <div className="space-y-4">
      {/* Error Display */}
      {batchExtraction.error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <div className="flex items-start gap-3">
            <svg className="h-6 w-6 text-red-500 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <div>
              <h4 className="text-lg font-medium text-red-900 mb-1">Batch Extraction Error</h4>
              <p className="text-red-700">{batchExtraction.error}</p>
            </div>
          </div>
        </div>
      )}

      {/* Overview Section */}
      <CollapsibleSection 
        title="Batch Extraction Overview" 
        sectionId="overview"
        badge={
          <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${getStatusColor(batchExtraction.status)}`}>
            {batchExtraction.status}
          </span>
        }
      >
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <div className="flex items-center gap-2">
              <svg className="h-5 w-5 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              <span className="text-sm font-medium text-blue-900">Fields Required</span>
            </div>
            <div className="mt-2 text-2xl font-bold text-blue-900">{fieldCount}</div>
          </div>

          <div className="bg-green-50 border border-green-200 rounded-lg p-4">
            <div className="flex items-center gap-2">
              <svg className="h-5 w-5 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <span className="text-sm font-medium text-green-900">Fields Extracted</span>
            </div>
            <div className="mt-2 text-2xl font-bold text-green-900">{extractedCount}</div>
          </div>

          <div className="bg-purple-50 border border-purple-200 rounded-lg p-4">
            <div className="flex items-center gap-2">
              <svg className="h-5 w-5 text-purple-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <span className="text-sm font-medium text-purple-900">Duration</span>
            </div>
            <div className="mt-2 text-lg font-bold text-purple-900">
              {calculateDuration(batchExtraction.start_time, batchExtraction.end_time)}
            </div>
          </div>

          <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
            <div className="flex items-center gap-2">
              <svg className="h-5 w-5 text-gray-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 9l3 3-3 3m5 0h3M5 20h14a2 2 0 002-2V6a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
              </svg>
              <span className="text-sm font-medium text-gray-900">LLM Calls</span>
            </div>
            <div className="mt-2 text-lg font-bold text-gray-900">
              {[batchExtraction.context_analysis_call, batchExtraction.batch_extraction_call].filter(Boolean).length}
            </div>
          </div>
        </div>

        <div className="mt-4 text-sm text-gray-600">
          <div className="flex items-center gap-2">
            <InfoIconWithTooltip tooltip="Batch extraction processes all input fields simultaneously using LLM tool schema, improving efficiency over individual field extraction." />
            <span>
              Started: {formatTime(batchExtraction.start_time)} | 
              Ended: {formatTime(batchExtraction.end_time)}
            </span>
          </div>
        </div>
      </CollapsibleSection>

      {/* Field Descriptions & Results */}
      <CollapsibleSection title="Field Extraction Results" sectionId="fields">
        <div className="space-y-4">
          {Object.entries(batchExtraction.input_descriptions || {}).map(([fieldName, description]) => {
            const extractedValue = batchExtraction.extracted_values?.[fieldName];
            const generatedPath = batchExtraction.generated_paths?.[fieldName];
            const hasValue = extractedValue && extractedValue !== '<NOT_FOUND_IN_CANDIDATES>';
            
            return (
              <div key={fieldName} className={`border rounded-lg p-4 ${hasValue ? 'bg-green-50 border-green-200' : 'bg-red-50 border-red-200'}`}>
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-2">
                      <span className="font-mono font-medium text-blue-600">{fieldName}</span>
                      {hasValue ? (
                        <svg className="h-4 w-4 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                      ) : (
                        <svg className="h-4 w-4 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                        </svg>
                      )}
                    </div>
                    <p className="text-sm text-gray-600 mb-3">{description}</p>
                    
                    <div className="space-y-2">
                      <div>
                        <label className="text-xs font-medium text-gray-700">Extracted Value:</label>
                        <div className={`mt-1 p-2 border rounded text-sm ${hasValue ? 'bg-white border-green-300' : 'bg-red-100 border-red-300'}`}>
                          {hasValue ? (
                            <span className="text-gray-900">{extractedValue}</span>
                          ) : (
                            <span className="text-red-700 font-medium">{extractedValue || 'Not found'}</span>
                          )}
                        </div>
                      </div>
                      
                      {hasValue && generatedPath && (
                        <div>
                          <label className="text-xs font-medium text-gray-700">JSON Path:</label>
                          <div className="mt-1 p-2 bg-white border border-gray-300 rounded">
                            <code className="text-xs font-mono text-purple-600">{generatedPath}</code>
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </CollapsibleSection>

      {/* Tool Schema */}
      {batchExtraction.tool_schema && (
        <CollapsibleSection title="Tool Schema" sectionId="schema">
          <div>
            <p className="text-sm text-gray-600 mb-3">
              The LLM tool schema used for batch field extraction:
            </p>
            <pre className="bg-gray-900 text-gray-100 p-4 rounded-lg overflow-x-auto text-sm">
              {JSON.stringify(batchExtraction.tool_schema, null, 2)}
            </pre>
          </div>
        </CollapsibleSection>
      )}

      {/* Candidate Fields */}
      {batchExtraction.candidate_fields && Object.keys(batchExtraction.candidate_fields).length > 0 && (
        <CollapsibleSection title="Context Candidates" sectionId="candidates">
          <div>
            <p className="text-sm text-gray-600 mb-3">
              Context fields analyzed as potential sources for extraction:
            </p>
            <div className="space-y-3">
              {Object.entries(batchExtraction.candidate_fields).map(([path, value]) => (
                <div key={path} className="border rounded-lg p-3 bg-gray-50">
                  <div className="flex items-start gap-3">
                    <code className="text-sm font-mono text-blue-600 mt-1">{path}:</code>
                    <div className="flex-1 min-w-0">
                      <div className="bg-white border rounded p-2 text-sm">
                        <pre className="whitespace-pre-wrap break-words text-gray-900">
                          {typeof value === 'string' ? value : JSON.stringify(value, null, 2)}
                        </pre>
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </CollapsibleSection>
      )}

      {/* LLM Calls */}
      <div className="space-y-4">
        {batchExtraction.context_analysis_call && (
          <CollapsibleSection title="Context Analysis LLM Call" sectionId="context-llm">
            <ContextualLLMCall 
              llmCall={batchExtraction.context_analysis_call}
              context="field_extraction"
            />
          </CollapsibleSection>
        )}
        
        {batchExtraction.batch_extraction_call && (
          <CollapsibleSection title="Batch Extraction LLM Call" sectionId="batch-llm">
            <ContextualLLMCall 
              llmCall={batchExtraction.batch_extraction_call}
              context="field_extraction"
            />
          </CollapsibleSection>
        )}
      </div>
    </div>
  );
};
