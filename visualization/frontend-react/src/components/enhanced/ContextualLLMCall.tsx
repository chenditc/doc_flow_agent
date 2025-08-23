import React, { useState } from 'react';
import type { LLMCall } from '../../types/trace';

interface ContextualLLMCallProps {
  llmCall: LLMCall;
  context: 'sop_validation' | 'field_extraction' | 'output_generation' | 'task_generation';
  relatedData?: any;
}

export const ContextualLLMCall: React.FC<ContextualLLMCallProps> = ({ 
  llmCall,
  context: _context,
  relatedData
}) => {
  const [isExpanded, setIsExpanded] = useState(false);

  const calculateDuration = (startTime: string, endTime: string): string => {
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
    <div className="space-y-3">
      {/* Metadata */}
      <div className="grid grid-cols-2 gap-4 text-sm">
        <div>
          <span className="font-medium text-gray-700">Model:</span>
          <span className="ml-2 text-gray-600">{llmCall.model || 'N/A'}</span>
        </div>
        <div>
          <span className="font-medium text-gray-700">Duration:</span>
          <span className="ml-2 text-gray-600">{calculateDuration(llmCall.start_time, llmCall.end_time)}</span>
        </div>
      </div>

      {/* Content Toggle */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full px-3 py-2 text-left bg-gray-50 hover:bg-gray-100 focus:outline-none focus:bg-gray-100 transition-colors border rounded text-sm"
      >
        <div className="flex items-center justify-between">
          <span className="font-medium text-gray-900">
            {isExpanded ? 'Hide' : 'Show'} Prompt & Response
          </span>
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
        <div className="space-y-3">
          {/* Prompt */}
          <div>
            <div className="text-sm font-medium text-gray-700 mb-2">Prompt</div>
            <div className="bg-white border rounded p-3">
              <div className="text-sm text-gray-700 whitespace-pre-wrap max-h-64 overflow-y-auto">
                {llmCall.prompt || 'No prompt available'}
              </div>
            </div>
          </div>

          {/* Response */}
          <div>
            <div className="text-sm font-medium text-gray-700 mb-2">Response</div>
            <div className="bg-white border rounded p-3">
              <div className="text-sm text-gray-700 whitespace-pre-wrap max-h-64 overflow-y-auto">
                {llmCall.response || 'No response available'}
              </div>
            </div>
          </div>

          {/* Token Usage */}
          {llmCall.token_usage && (
            <div>
              <div className="text-sm font-medium text-gray-700 mb-2">Token Usage</div>
              <div className="bg-white border rounded p-3">
                <div className="text-sm text-gray-700">
                  <pre>{JSON.stringify(llmCall.token_usage, null, 2)}</pre>
                </div>
              </div>
            </div>
          )}

          {/* Related Data */}
          {relatedData && (
            <div>
              <div className="text-sm font-medium text-gray-700 mb-2">Related Data</div>
              <div className="bg-white border rounded p-3">
                <div className="text-sm text-gray-700">
                  <pre>{JSON.stringify(relatedData, null, 2)}</pre>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
