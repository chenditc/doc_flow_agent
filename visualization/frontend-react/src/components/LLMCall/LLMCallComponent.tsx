import React from 'react';
import type { LLMCall } from '../../types/trace';

interface LLMCallComponentProps {
  llmCall: LLMCall;
}

export const LLMCallComponent: React.FC<LLMCallComponentProps> = ({ llmCall }) => {
  const formatTime = (timestamp: string): string => {
    if (!timestamp) return 'N/A';
    try {
      return new Date(timestamp).toLocaleString();
    } catch (error) {
      return 'Invalid time';
    }
  };

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
    <div className="bg-purple-50 border border-purple-200 rounded-lg p-4">
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <h4 className="text-sm font-medium text-purple-900">LLM Call</h4>
        <div className="text-xs text-purple-600">
          {formatTime(llmCall.start_time)} • {calculateDuration(llmCall.start_time, llmCall.end_time)}
        </div>
      </div>

      {/* Metadata */}
      <div className="grid grid-cols-2 gap-4 text-sm mb-4">
        <div>
          <span className="font-medium text-purple-700">Model:</span>
          <span className="ml-2 text-purple-600">{llmCall.model || 'N/A'}</span>
        </div>
        <div>
          <span className="font-medium text-purple-700">Step:</span>
          <span className="ml-2 text-purple-600">N/A</span>
        </div>
      </div>

      {/* Prompt */}
      <div className="space-y-3">
        <div>
          <div className="text-sm font-medium text-purple-700 mb-2">Prompt</div>
          <div className="bg-white border rounded p-3">
            <div className="text-sm text-gray-700 whitespace-pre-wrap max-h-40 overflow-y-auto">
              {llmCall.prompt || 'No prompt available'}
            </div>
          </div>
        </div>

        {/* Response */}
        <div>
          <div className="text-sm font-medium text-purple-700 mb-2">Response</div>
          <div className="bg-white border rounded p-3">
            <div className="text-sm text-gray-700 whitespace-pre-wrap max-h-40 overflow-y-auto">
              {llmCall.response || 'No response available'}
            </div>
          </div>
        </div>

        {/* Token Usage */}
        {llmCall.token_usage && (
          <div>
            <div className="text-sm font-medium text-purple-700 mb-2">Token Usage</div>
            <div className="bg-white border rounded p-3">
              <div className="text-sm text-gray-700">
                <pre>{JSON.stringify(llmCall.token_usage, null, 2)}</pre>
              </div>
            </div>
          </div>
        )}

        {/* Tool Call ID */}
        <div>
          <div className="text-sm font-medium text-purple-700 mb-2">Tool Call ID</div>
          <div className="bg-white border rounded p-3">
            <div className="text-sm font-mono text-gray-700">
              {llmCall.tool_call_id}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
