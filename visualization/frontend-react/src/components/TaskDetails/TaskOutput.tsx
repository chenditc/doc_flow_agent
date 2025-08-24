import React from 'react';
import ReactMarkdown from 'react-markdown';
import type { TaskExecution } from '../../types/trace';
import { ContextualLLMCall } from '../enhanced/ContextualLLMCall';
import { CliOutput } from '../common/CliOutput';

interface TaskOutputProps {
  task: TaskExecution;
}

export const TaskOutput: React.FC<TaskOutputProps> = ({ task }) => {
  const extractTaskOutput = (task: TaskExecution): { type: 'llm', data: any } | { type: 'cli', data: { stdout?: string, stderr?: string } } | { type: 'object', data: any } | { type: 'string', data: string } | { type: 'none' } => {
    // Try to get from engine_state_after.context.last_task_output
    if (task.engine_state_after && 
        task.engine_state_after.context && 
        task.engine_state_after.context.last_task_output) {
      
      const output = task.engine_state_after.context.last_task_output;
      
      if (typeof output === 'string') {
        return { type: 'string', data: output };
      } else if (typeof output === 'object' && output !== null) {
        // Check if it has content and tool_calls (LLM response format)
        if (output.content || output.tool_calls) {
          return { type: 'llm', data: output };
        }
        
        // Check if it only contains stdout and/or stderr
        const keys = Object.keys(output);
        const isOnlyCliOutput = keys.every(key => ['stdout', 'stderr'].includes(key));
        
        if (isOnlyCliOutput && (output.stdout || output.stderr)) {
          return { 
            type: 'cli', 
            data: { 
              stdout: output.stdout, 
              stderr: output.stderr 
            } 
          };
        }
        
        // For other objects, return as object type
        return { type: 'object', data: output };
      }
    }
    
    // Look for context_update phase with updated_paths
    if (task.phases && task.phases.context_update) {
      if (task.engine_state_after && task.engine_state_after.context) {
        const context = task.engine_state_after.context;
        // Try to extract meaningful output from context
        const contextEntries = Object.entries(context)
          .filter(([key]) => !['task_stack', 'task_execution_counter'].includes(key));
        
        if (contextEntries.length > 0) {
          const contextObject = Object.fromEntries(contextEntries);
          return { type: 'object', data: contextObject };
        }
      }
    }
    
    return { type: 'none' };
  };

  const renderOutput = (output: ReturnType<typeof extractTaskOutput>) => {
    switch (output.type) {
      case 'llm':
        const responseContent = output.data.content || '';
        return (
          <div className="space-y-4">
            {/* Markdown Response Display */}
            {responseContent && (
              <div className="bg-white border rounded-md shadow-sm">
                <div className="px-3 py-2 border-b bg-blue-50 flex items-center justify-between">
                  <span className="text-xs font-medium text-blue-700 uppercase">LLM Response</span>
                  <button
                    onClick={() => navigator.clipboard.writeText(responseContent)}
                    className="text-xs text-blue-500 hover:text-blue-700 focus:outline-none focus:text-blue-700"
                    title="Copy response to clipboard"
                  >
                    <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                    </svg>
                  </button>
                </div>
                <div className="p-4">
                  <div className="prose prose-sm max-w-none text-gray-800">
                    <ReactMarkdown
                      components={{
                        // Custom styling for code blocks
                        code: (props) => {
                          const { children, ...rest } = props;
                          return (
                            <code
                              className="bg-gray-100 text-gray-800 px-1 py-0.5 rounded text-sm font-mono"
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
                              className="bg-gray-100 p-3 rounded-md overflow-x-auto mb-3"
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
                            <h1 className="text-xl font-bold text-gray-900 mb-3 mt-4 first:mt-0" {...rest}>
                              {children}
                            </h1>
                          );
                        },
                        h2: (props) => {
                          const { children, ...rest } = props;
                          return (
                            <h2 className="text-lg font-semibold text-gray-800 mb-2 mt-3 first:mt-0" {...rest}>
                              {children}
                            </h2>
                          );
                        },
                        h3: (props) => {
                          const { children, ...rest } = props;
                          return (
                            <h3 className="text-base font-semibold text-gray-800 mb-2 mt-3 first:mt-0" {...rest}>
                              {children}
                            </h3>
                          );
                        },
                        // Custom styling for lists
                        ul: (props) => {
                          const { children, ...rest } = props;
                          return (
                            <ul className="list-disc pl-5 mb-3 space-y-1" {...rest}>
                              {children}
                            </ul>
                          );
                        },
                        ol: (props) => {
                          const { children, ...rest } = props;
                          return (
                            <ol className="list-decimal pl-5 mb-3 space-y-1" {...rest}>
                              {children}
                            </ol>
                          );
                        },
                        // Custom styling for paragraphs
                        p: (props) => {
                          const { children, ...rest } = props;
                          return (
                            <p className="mb-3 text-gray-800 leading-relaxed" {...rest}>
                              {children}
                            </p>
                          );
                        },
                        // Custom styling for blockquotes
                        blockquote: (props) => {
                          const { children, ...rest } = props;
                          return (
                            <blockquote className="border-l-4 border-blue-200 pl-4 italic text-gray-700 mb-3" {...rest}>
                              {children}
                            </blockquote>
                          );
                        },
                      }}
                    >
                      {responseContent}
                    </ReactMarkdown>
                  </div>
                </div>
              </div>
            )}
            
            {/* Detailed LLM Call Information */}
            <ContextualLLMCall
              llmCall={{
                tool_call_id: 'output-display',
                prompt: '',
                response: responseContent,
                tool_calls: output.data.tool_calls || [],
                model: '',
                start_time: '',
                end_time: ''
              }}
              context="output_generation"
              relatedData={output.data}
            />
          </div>
        );
        
      case 'cli':
        return (
          <CliOutput
            stdout={output.data.stdout}
            stderr={output.data.stderr}
            title="Task Output"
          />
        );
        
      case 'object':
        return (
          <div className="bg-gray-50 border rounded-md">
            <div className="px-3 py-2 border-b bg-gray-100 flex items-center justify-between">
              <span className="text-xs font-medium text-gray-700 uppercase">Output</span>
              <button
                onClick={() => navigator.clipboard.writeText(JSON.stringify(output.data, null, 2))}
                className="text-xs text-gray-500 hover:text-gray-700 focus:outline-none focus:text-gray-700"
                title="Copy to clipboard"
              >
                <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                </svg>
              </button>
            </div>
            <div className="p-4 space-y-3">
              {Object.entries(output.data).map(([key, value]) => (
                <div key={key} className="border-b border-gray-200 pb-2 last:border-b-0">
                  <dt className="text-sm font-medium text-gray-600 mb-1">{key}:</dt>
                  <dd className="text-sm text-gray-800">
                    <pre className="whitespace-pre-wrap break-words">
                      {typeof value === 'object' ? JSON.stringify(value, null, 2) : String(value)}
                    </pre>
                  </dd>
                </div>
              ))}
            </div>
          </div>
        );
        
      case 'string':
        return (
          <div className="bg-gray-50 border rounded-md">
            <div className="px-3 py-2 border-b bg-gray-100 flex items-center justify-between">
              <span className="text-xs font-medium text-gray-700 uppercase">Output</span>
              <button
                onClick={() => navigator.clipboard.writeText(output.data)}
                className="text-xs text-gray-500 hover:text-gray-700 focus:outline-none focus:text-gray-700"
                title="Copy to clipboard"
              >
                <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                </svg>
              </button>
            </div>
            <div className="p-4">
              <pre className="text-sm text-gray-800 whitespace-pre-wrap break-words max-h-96 overflow-y-auto">
                {output.data}
              </pre>
            </div>
          </div>
        );
        
      case 'none':
      default:
        return (
          <div className="bg-gray-50 border-2 border-dashed border-gray-300 rounded-md p-8 text-center">
            <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            <h3 className="mt-4 text-sm font-medium text-gray-900">No output available</h3>
            <p className="mt-2 text-sm text-gray-500">
              This task did not produce any output or the output is not available.
            </p>
          </div>
        );
    }
  };

  const output = extractTaskOutput(task);

  return (
    <div className="space-y-4">
      <div>
        <h3 className="text-lg font-medium text-gray-900 mb-3">Task Output</h3>
        {renderOutput(output)}
      </div>
    </div>
  );
};
