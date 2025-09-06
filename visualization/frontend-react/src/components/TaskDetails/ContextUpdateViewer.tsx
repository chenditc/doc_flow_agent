import React, { useState } from 'react';
import type { ContextUpdatePhase } from '../../types/trace';
import { ContextualLLMCall } from '../enhanced/ContextualLLMCall';

interface ContextUpdateViewerProps {
  phaseData: ContextUpdatePhase;
}

interface CollapsibleSectionProps {
  title: string;
  children: React.ReactNode;
  defaultExpanded?: boolean;
}

const CollapsibleSection: React.FC<CollapsibleSectionProps> = ({ 
  title, 
  children, 
  defaultExpanded = false 
}) => {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);

  return (
    <div className="border rounded-md">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full px-4 py-3 text-left bg-gray-50 hover:bg-gray-100 focus:outline-none focus:bg-gray-100 transition-colors border-b border-gray-200 rounded-t-md"
      >
        <div className="flex items-center justify-between">
          <span className="font-medium text-gray-900">{title}</span>
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

const KeyValueDisplay: React.FC<{ data: Record<string, any>; title: string }> = ({ data, title }) => {
  const entries = Object.entries(data);
  
  if (entries.length === 0) {
    return (
      <div className="text-sm text-gray-500 italic">
        No {title.toLowerCase()} data available
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {entries.map(([key, value]) => (
        <div key={key} className="border-l-4 border-blue-200 pl-4">
          <div className="flex items-start gap-2">
            <code className="text-sm font-semibold text-blue-700 bg-blue-50 px-2 py-1 rounded">
              {key}
            </code>
          </div>
          <div className="mt-2">
            {typeof value === 'string' ? (
              <div className="text-sm text-gray-800 whitespace-pre-wrap bg-gray-50 p-3 rounded border">
                {value}
              </div>
            ) : (
              <pre className="text-xs text-gray-700 bg-gray-50 p-3 rounded border overflow-x-auto max-h-64 overflow-y-auto">
                {JSON.stringify(value, null, 2)}
              </pre>
            )}
          </div>
        </div>
      ))}
    </div>
  );
};

export const ContextUpdateViewer: React.FC<ContextUpdateViewerProps> = ({ phaseData }) => {
  const hasUpdatedPaths = phaseData.updated_paths && phaseData.updated_paths.length > 0;
  const hasRemovedTempKeys = phaseData.removed_temp_keys && phaseData.removed_temp_keys.length > 0;
  const hasOutputPathGeneration = phaseData.output_path_generation;

  return (
    <div className="space-y-6">
      {/* Updated Paths - prominently displayed */}
      {hasUpdatedPaths && (
        <div>
          <h4 className="text-sm font-medium text-gray-900 mb-3">Updated Paths</h4>
          <div className="flex flex-wrap gap-2">
            {phaseData.updated_paths.map((path, index) => (
              <span 
                key={index}
                className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-green-100 text-green-800"
              >
                <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <code className="text-xs">{path}</code>
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Removed Temp Keys */}
      {hasRemovedTempKeys && (
        <div>
          <h4 className="text-sm font-medium text-gray-900 mb-3">Removed Temporary Keys</h4>
          <div className="flex flex-wrap gap-2">
            {phaseData.removed_temp_keys.map((key, index) => (
              <span 
                key={index}
                className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-red-100 text-red-800"
              >
                <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
                <code className="text-xs">{key}</code>
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Output Path Generation */}
      {hasOutputPathGeneration && phaseData.output_path_generation && (
        <div>
          <h4 className="text-sm font-medium text-gray-900 mb-3">Output Path Generation</h4>
          <div className="p-3 bg-gray-50 border rounded text-sm space-y-2">
            <div>
              <span className="font-medium text-gray-700">Generated Path:</span>
              <code className="ml-2 font-mono bg-white px-2 py-1 rounded">
                {phaseData.output_path_generation.generated_path || 'N/A'}
              </code>
            </div>
            <div>
              <span className="font-medium text-gray-700">Prefixed Path:</span>
              <code className="ml-2 font-mono bg-white px-2 py-1 rounded">
                {phaseData.output_path_generation.prefixed_path || 'N/A'}
              </code>
            </div>
            
            {(phaseData.output_path_generation as any)?.llm_calls && (phaseData.output_path_generation as any).llm_calls.length > 0 ? (
              <CollapsibleSection title="View Path Generation Calls" defaultExpanded={false}>
                <div className="space-y-3">
                  {(phaseData.output_path_generation as any).llm_calls.map((call: any, idx: number) => (
                    <ContextualLLMCall key={call.tool_call_id || idx} llmCall={call} context="output_generation" />
                  ))}
                </div>
              </CollapsibleSection>
            ) : (phaseData.output_path_generation as any)?.path_generation_call ? (
              <CollapsibleSection title="View Path Generation Call" defaultExpanded={false}>
                <ContextualLLMCall llmCall={(phaseData.output_path_generation as any).path_generation_call} context="output_generation" />
              </CollapsibleSection>
            ) : null}
            
            {phaseData.output_path_generation.error && (
              <div className="bg-red-50 border border-red-200 rounded-lg p-3">
                <div className="text-red-700 text-sm">{phaseData.output_path_generation.error}</div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Context Before/After in collapsible sections */}
      <div className="space-y-3">
        <CollapsibleSection title="Context Before" defaultExpanded={false}>
          <KeyValueDisplay data={phaseData.context_before} title="Context Before" />
        </CollapsibleSection>

        <CollapsibleSection title="Context After" defaultExpanded={false}>
          <KeyValueDisplay data={phaseData.context_after} title="Context After" />
        </CollapsibleSection>
      </div>

      {/* Error Display */}
      {phaseData.error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-3">
          <h4 className="text-sm font-medium text-red-800 mb-1">Error</h4>
          <div className="text-red-700 text-sm">{phaseData.error}</div>
        </div>
      )}
    </div>
  );
};
