import React from 'react';
import type { TaskExecution } from '../../types/trace';

interface TaskOutputProps {
  task: TaskExecution;
}

export const TaskOutput: React.FC<TaskOutputProps> = ({ task }) => {
  const extractTaskOutput = (task: TaskExecution): string => {
    // Try to get from engine_state_after.context.last_task_output
    if (task.engine_state_after && 
        task.engine_state_after.context && 
        task.engine_state_after.context.last_task_output) {
      
      const output = task.engine_state_after.context.last_task_output;
      
      if (typeof output === 'string') {
        return output;
      } else if (typeof output === 'object' && output !== null) {
        if (output.stdout || output.stderr) {
          let result = '';
          if (output.stdout) result += output.stdout;
          if (output.stderr) result += (result ? '\n--- STDERR ---\n' : '') + output.stderr;
          return result || 'No output';
        } else {
          return JSON.stringify(output, null, 2);
        }
      }
    }
    
    // Look for context_update phase with updated_paths
    if (task.phases && task.phases.context_update) {
      if (task.engine_state_after && task.engine_state_after.context) {
        const context = task.engine_state_after.context;
        // Try to extract meaningful output from context
        const contextEntries = Object.entries(context)
          .filter(([key]) => !['task_stack', 'task_execution_counter'].includes(key))
          .map(([key, value]) => `${key}: ${typeof value === 'object' ? JSON.stringify(value, null, 2) : value}`)
          .join('\n');
        
        if (contextEntries) {
          return `Context updates:\n${contextEntries}`;
        }
      }
    }
    
    return 'No output available';
  };

  const output = extractTaskOutput(task);
  const hasOutput = output && output !== 'No output available';

  return (
    <div className="space-y-4">
      <div>
        <h3 className="text-lg font-medium text-gray-900 mb-3">Task Output</h3>
        
        {hasOutput ? (
          <div className="bg-gray-50 border rounded-md">
            <div className="px-3 py-2 border-b bg-gray-100 flex items-center justify-between">
              <span className="text-xs font-medium text-gray-700 uppercase">Output</span>
              <button
                onClick={() => navigator.clipboard.writeText(output)}
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
                {output}
              </pre>
            </div>
          </div>
        ) : (
          <div className="bg-gray-50 border-2 border-dashed border-gray-300 rounded-md p-8 text-center">
            <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            <h3 className="mt-4 text-sm font-medium text-gray-900">No output available</h3>
            <p className="mt-2 text-sm text-gray-500">
              This task did not produce any output or the output is not available.
            </p>
          </div>
        )}
      </div>
    </div>
  );
};
