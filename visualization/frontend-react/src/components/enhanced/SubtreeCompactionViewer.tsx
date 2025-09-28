import React, { useState } from 'react';
import type { SubtreeCompactionPhase } from '../../types/trace';
import { ContextualLLMCall } from './ContextualLLMCall';
import { JsonViewer as NiceJsonViewer } from '../common/JsonViewer';

interface SubtreeCompactionViewerProps {
  phaseData: SubtreeCompactionPhase;
}

interface CollapsibleSectionProps {
  title: React.ReactNode;
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
          <div className="font-medium text-gray-900">{title}</div>
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

export const SubtreeCompactionViewer: React.FC<SubtreeCompactionViewerProps> = ({ phaseData }) => {
  // Extract useful output paths from LLM tool calls if present
  const getUsefulOutputPaths = (): string[] => {
    if (!phaseData.llm_calls || phaseData.llm_calls.length === 0) return [];
    
    const paths: string[] = [];
    phaseData.llm_calls.forEach(call => {
      call.tool_calls?.forEach(toolCall => {
        if (toolCall.arguments?.useful_output_path) {
          const usefulPaths = Array.isArray(toolCall.arguments.useful_output_path) 
            ? toolCall.arguments.useful_output_path 
            : [toolCall.arguments.useful_output_path];
          paths.push(...usefulPaths);
        }
      });
    });
    return [...new Set(paths)]; // Remove duplicates
  };

  const usefulOutputPaths = getUsefulOutputPaths();
  const aggregatedOutputKeys = Object.keys(phaseData.aggregated_outputs || {});
  const subtreeTaskCount = phaseData.subtree_task_ids?.length || 0;

  return (
    <div className="space-y-4">
      {/* Summary Information */}
      <div className="grid grid-cols-2 gap-4 text-sm">
        <div>
          <span className="font-medium text-gray-700">Root Task ID:</span>
          <code className="ml-2 font-mono text-blue-600">{phaseData.root_task_id}</code>
        </div>
        <div>
          <span className="font-medium text-gray-700">Subtree Tasks:</span>
          <span className="ml-2 text-gray-600">{subtreeTaskCount}</span>
        </div>
      </div>

      {/* Useful Output Paths (if any) */}
      {usefulOutputPaths.length > 0 && (
        <div>
          <div className="text-sm font-medium text-gray-700 mb-2">Useful Output Paths</div>
          <div className="flex flex-wrap gap-2">
            {usefulOutputPaths.map((path, index) => (
              <span
                key={index}
                className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800"
              >
                {path}
              </span>
            ))}
          </div>
        </div>
      )}


      {/* Aggregated Outputs (always show header for count consistency, even if zero) */}
      <div>
        <div className="text-sm font-medium text-gray-700 mb-2">
          Aggregated Outputs ({aggregatedOutputKeys.length})
        </div>
        {aggregatedOutputKeys.length > 0 && (
          <div className="space-y-2">
            {aggregatedOutputKeys.map((outputPath, index) => {
              const isUseful = usefulOutputPaths.includes(outputPath);
              const outputData = phaseData.aggregated_outputs[outputPath];
              
              return (
                <CollapsibleSection
                  key={index}
                  title={
                    isUseful
                      // Avoid duplicating the raw path text which already appears in Useful Output Paths badges
                      ? (
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-mono text-gray-600">Useful Output</span>
                          <span className="inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium bg-green-100 text-green-800">
                            useful
                          </span>
                        </div>
                        )
                      : (
                        <div className="flex items-center gap-2">
                          <code className="text-sm font-mono">{outputPath}</code>
                        </div>
                        )
                  }
                  defaultExpanded={false}
                >
                  <div className="text-xs text-gray-700 bg-gray-50 p-3 rounded border overflow-x-auto">
                    <NiceJsonViewer value={outputData} label="Outputs" collapsed={false} />
                  </div>
                </CollapsibleSection>
              );
            })}
          </div>
        )}
      </div>

      {/* LLM Calls */}
      <div>
        <div className="text-sm font-medium text-gray-700 mb-2">
          LLM Calls ({phaseData.llm_calls?.length || 0})
        </div>
        {phaseData.llm_calls && phaseData.llm_calls.length > 0 ? (
          <div className="space-y-3">
            {phaseData.llm_calls.map((call, index) => (
              <div key={call.tool_call_id || index} className="border rounded p-3">
                <ContextualLLMCall 
                  llmCall={call} 
                  context="subtree_compaction" 
                  relatedData={phaseData.aggregated_outputs}
                  // Keep collapsed by default so tests can find and click the 'Show Prompt & Response' button
                />
              </div>
            ))}
          </div>
        ) : (
          <div className="bg-gray-50 border rounded p-3">
            <div className="text-sm text-gray-400 italic">No LLM calls recorded</div>
          </div>
        )}
      </div>

      {/* Error Display */}
      {phaseData.error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-3">
          <div className="text-red-700 text-sm">{phaseData.error}</div>
        </div>
      )}
    </div>
  );
};