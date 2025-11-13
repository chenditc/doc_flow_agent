import React, { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import type { LLMCall } from '../../types/trace';
import { JsonViewer as NiceJsonViewer } from '../common/JsonViewer';

interface ContextualLLMCallProps {
  llmCall: LLMCall;
  context: 'sop_validation' | 'field_extraction' | 'output_generation' | 'task_generation' | 'subtree_compaction';
  relatedData?: any;
  defaultExpanded?: boolean;
}

export const ContextualLLMCall: React.FC<ContextualLLMCallProps> = ({ 
  llmCall,
  context: _context,
  relatedData,
  defaultExpanded = false
}) => {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);
  const [copyFeedback, setCopyFeedback] = useState<string | null>(null);
  const [responseCopyFeedback, setResponseCopyFeedback] = useState<string | null>(null);

  const handleCopyPrompt = async () => {
    try {
      await navigator.clipboard.writeText(llmCall.prompt || '');
      setCopyFeedback('Copied!');
      setTimeout(() => setCopyFeedback(null), 2000);
    } catch (err) {
      setCopyFeedback('Failed to copy');
      setTimeout(() => setCopyFeedback(null), 2000);
    }
  };

  const handleCopyResponse = async () => {
    try {
      await navigator.clipboard.writeText(llmCall.response || '');
      setResponseCopyFeedback('Copied!');
      setTimeout(() => setResponseCopyFeedback(null), 2000);
    } catch (err) {
      setResponseCopyFeedback('Failed to copy');
      setTimeout(() => setResponseCopyFeedback(null), 2000);
    }
  };

  const handleOpenTuningPage = () => {
    // Collect all the parameters for the tuning page
    const allParameters = {
      model: llmCall.model,
      temperature: 0.7, // default, can be overridden
      max_tokens: 5000, // default, can be overridden
      ...(llmCall.token_usage ? { token_usage: llmCall.token_usage } : {}),
      start_time: llmCall.start_time,
      end_time: llmCall.end_time,
      ...(relatedData ? { related_data: relatedData } : {}),
    };

    // Prepare URL parameters - iterate through all_parameters if available
    const params = new URLSearchParams();
    
    // If llmCall has all_parameters, use those directly
    if (llmCall.all_parameters) {
      Object.entries(llmCall.all_parameters).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
          // For objects and arrays, stringify them
          const stringValue = typeof value === 'object' ? JSON.stringify(value) : String(value);
          params.set(key, encodeURIComponent(stringValue));
        }
      });
    } else {
      // Fallback: use individual fields if all_parameters is not available
      if (llmCall.prompt) {
        params.set('prompt', encodeURIComponent(llmCall.prompt));
      }
      
      if (llmCall.tool_calls && llmCall.tool_calls.length > 0) {
        // Convert tool calls to OpenAI function calling format
        const tools = llmCall.tool_calls.map(toolCall => ({
          type: "function",
          function: {
            name: toolCall.name,
            description: `Tool call: ${toolCall.name}`,
            parameters: toolCall.arguments || {}
          }
        }));
        params.set('tools', encodeURIComponent(JSON.stringify(tools)));
      }
    }
    
    // Always add the additional parameters
    params.set('all_parameters', encodeURIComponent(JSON.stringify(allParameters, null, 2)));

    // Open the tuning page in a new tab
    const tuningUrl = `/llm-tuning?${params.toString()}`;
    window.open(tuningUrl, '_blank');
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
    <div className="space-y-3">
      {/* Metadata */}
      <div className="flex flex-wrap gap-x-6 gap-y-2 text-sm text-gray-700">
        <div className="whitespace-nowrap">
          <span className="font-medium">Model:</span>
          <span className="ml-2 text-gray-600">{llmCall.model || 'N/A'}</span>
        </div>
        <div className="whitespace-nowrap">
          <span className="font-medium">Duration:</span>
          <span className="ml-2 text-gray-600">{calculateDuration(llmCall.start_time, llmCall.end_time)}</span>
        </div>
        {llmCall.token_usage?.prompt_tokens !== undefined && (
          <div className="whitespace-nowrap">
            <span className="font-medium">Prompt Tokens:</span>
            <span className="ml-2 text-gray-600">{llmCall.token_usage.prompt_tokens}</span>
          </div>
        )}
        {llmCall.token_usage?.completion_tokens !== undefined && (
          <div className="whitespace-nowrap">
            <span className="font-medium">Completion Tokens:</span>
            <span className="ml-2 text-gray-600">{llmCall.token_usage.completion_tokens}</span>
          </div>
        )}
        {llmCall.token_usage?.total_tokens !== undefined && (
          <div className="whitespace-nowrap">
            <span className="font-medium">Total Tokens:</span>
            <span className="ml-2 text-gray-600">{llmCall.token_usage.total_tokens}</span>
          </div>
        )}
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
            <div className="flex items-center justify-between mb-2">
              <div className="text-sm font-medium text-gray-700">Prompt</div>
              <div className="flex items-center space-x-2">
                {copyFeedback && (
                  <span className={`text-xs ${
                    copyFeedback === 'Copied!' ? 'text-green-600' : 'text-red-600'
                  }`}>
                    {copyFeedback}
                  </span>
                )}
                <button
                  onClick={handleCopyPrompt}
                  className="text-gray-500 hover:text-gray-700 focus:outline-none focus:text-gray-700 p-1"
                  title="Copy prompt to clipboard"
                >
                  <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                  </svg>
                </button>
              </div>
            </div>
            <div className="bg-white border rounded p-3">
              <div className="text-sm text-gray-700 whitespace-pre-wrap max-h-64 overflow-y-auto">
                {llmCall.prompt || 'No prompt available'}
              </div>
            </div>
          </div>

          {/* Response */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <div className="text-sm font-medium text-gray-700">Response</div>
              <div className="flex items-center space-x-2">
                {responseCopyFeedback && (
                  <span className={`text-xs ${
                    responseCopyFeedback === 'Copied!' ? 'text-green-600' : 'text-red-600'
                  }`}>
                    {responseCopyFeedback}
                  </span>
                )}
                <button
                  onClick={handleCopyResponse}
                  className="text-gray-500 hover:text-gray-700 focus:outline-none focus:text-gray-700 p-1"
                  title="Copy response to clipboard"
                >
                  <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                  </svg>
                </button>
              </div>
            </div>
            <div className="bg-white border rounded p-3">
              <div className="prose prose-sm max-w-none max-h-64 overflow-y-auto">
                <ReactMarkdown
                  components={{
                    // Custom styling for code blocks
                    code: (props) => {
                      const { children, ...rest } = props;
                      return (
                        <code
                          className="bg-gray-100 text-gray-800 px-1 py-0.5 rounded text-xs font-mono"
                          {...rest}
                        >
                          {children}
                        </code>
                      );
                    },
                    pre: (props) => {
                      const { children, ...rest } = props;
                      return (
                        <pre 
                          className="bg-gray-100 p-2 rounded-md overflow-x-auto mb-2 text-xs"
                          {...rest}
                        >
                          {children}
                        </pre>
                      );
                    },
                    // Custom styling for headings
                    h1: (props) => {
                      const { children, ...rest } = props;
                      return (
                        <h1 className="text-base font-bold text-gray-900 mb-2 mt-3 first:mt-0" {...rest}>
                          {children}
                        </h1>
                      );
                    },
                    h2: (props) => {
                      const { children, ...rest } = props;
                      return (
                        <h2 className="text-sm font-semibold text-gray-800 mb-2 mt-2 first:mt-0" {...rest}>
                          {children}
                        </h2>
                      );
                    },
                    h3: (props) => {
                      const { children, ...rest } = props;
                      return (
                        <h3 className="text-sm font-semibold text-gray-800 mb-1 mt-2 first:mt-0" {...rest}>
                          {children}
                        </h3>
                      );
                    },
                    // Custom styling for lists
                    ul: (props) => {
                      const { children, ...rest } = props;
                      return (
                        <ul className="list-disc pl-4 mb-2 space-y-0.5 text-sm" {...rest}>
                          {children}
                        </ul>
                      );
                    },
                    ol: (props) => {
                      const { children, ...rest } = props;
                      return (
                        <ol className="list-decimal pl-4 mb-2 space-y-0.5 text-sm" {...rest}>
                          {children}
                        </ol>
                      );
                    },
                    // Custom styling for paragraphs
                    p: (props) => {
                      const { children, ...rest } = props;
                      return (
                        <p className="mb-2 text-sm text-gray-700 leading-relaxed" {...rest}>
                          {children}
                        </p>
                      );
                    },
                    // Custom styling for blockquotes
                    blockquote: (props) => {
                      const { children, ...rest } = props;
                      return (
                        <blockquote className="border-l-2 border-gray-300 pl-3 italic text-gray-600 mb-2 text-sm" {...rest}>
                          {children}
                        </blockquote>
                      );
                    },
                  }}
                >
                  {llmCall.response || 'No response available'}
                </ReactMarkdown>
              </div>
            </div>
          </div>

          {/* Tool Calls */}
          <div>
            <div className="text-sm font-medium text-gray-700 mb-2">Tool Calls</div>
            {llmCall.tool_calls && llmCall.tool_calls.length > 0 ? (
              <div className="space-y-2">
                {llmCall.tool_calls.map((toolCall, index) => (
                  <div key={toolCall.id || index} className="bg-blue-50 border border-blue-200 rounded p-3">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm font-semibold text-blue-800">
                        {toolCall.name}
                      </span>
                      <span className="text-xs text-blue-600 font-mono">
                        {toolCall.id}
                      </span>
                    </div>
                    <div className="text-sm text-gray-700 space-y-1">
                      <span className="font-medium block">Arguments:</span>
                      <div className="bg-white border border-blue-200 rounded p-2 text-xs">
                        <NiceJsonViewer value={toolCall.arguments} label="Arguments" collapsed={false} />
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="bg-gray-50 border rounded p-3">
                <div className="text-sm text-gray-400 italic">No tool call</div>
              </div>
            )}
          </div>

          {/* Token Usage */}
          {llmCall.token_usage && (
            <div>
              <div className="text-sm font-medium text-gray-700 mb-2">Token Usage</div>
              <div className="bg-white border rounded p-3 text-xs">
                <NiceJsonViewer value={llmCall.token_usage} label="Token Usage" collapsed={false} />
              </div>
            </div>
          )}

          {/* Related Data */}
          {relatedData && (
            <div>
              <div className="text-sm font-medium text-gray-700 mb-2">Related Data</div>
              <div className="bg-white border rounded p-3 text-xs">
                <NiceJsonViewer value={relatedData} label="Related Data" collapsed={false} />
              </div>
            </div>
          )}

          {/* Tune in LLM Tuning Page Button */}
          <div className="pt-3 border-t border-gray-200">
            <button
              onClick={handleOpenTuningPage}
              className="w-full px-4 py-2 bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 text-white font-medium rounded-md transition-colors text-sm"
            >
              🔧 Tune in LLM Tuning Page
            </button>
          </div>
        </div>
      )}
      {!isExpanded && (
        <div className="pt-2">
          <button
            onClick={handleOpenTuningPage}
            className="w-full px-2 py-1 bg-blue-50 hover:bg-blue-100 text-blue-700 rounded text-xs border border-blue-200"
          >
            🔧 Tune in LLM Tuning Page
          </button>
        </div>
      )}
    </div>
  );
};
