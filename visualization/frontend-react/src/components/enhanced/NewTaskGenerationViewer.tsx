import React from 'react';
import type { NewTaskGenerationPhase } from '../../types/trace';
import { ContextualLLMCall } from './ContextualLLMCall';

interface NewTaskGenerationViewerProps {
  phaseData: NewTaskGenerationPhase;
}

function renderGeneratedTask(task: any): React.ReactNode {
  if (typeof task === 'string') return task;
  if (!task || typeof task !== 'object') return String(task);
  // Prefer description if present
  if (typeof task.description === 'string') return task.description;
  // Fallback: pretty-print object
  return (
    <pre className="text-xs bg-white rounded border p-2 overflow-x-auto">
      {JSON.stringify(task, null, 2)}
    </pre>
  );
}

export const NewTaskGenerationViewer: React.FC<NewTaskGenerationViewerProps> = ({ phaseData }) => {
  const taskGeneration = phaseData.task_generation;
  
  if (!taskGeneration) {
    return (
      <div className="text-sm text-gray-500">
        No task generation data available
      </div>
    );
  }

  const generatedTasks = (taskGeneration.generated_tasks || []) as any[];
  const taskCount = generatedTasks.length;
  const llmCalls = (taskGeneration as any).llm_calls as any[] | undefined;
  const singleCall = (taskGeneration as any).task_generation_call as any | undefined;

  return (
    <div className="space-y-4">
      {/* Generated Tasks Display */}
      <div>
        <div className="text-sm font-medium text-gray-700 mb-3">
          Generated Tasks ({taskCount})
        </div>
        
        {taskCount === 0 ? (
          <div className="text-sm text-gray-500 italic bg-gray-50 p-3 rounded">
            No new tasks generated
          </div>
        ) : (
          <div className="space-y-2">
            {generatedTasks.map((task, index) => (
              <div 
                key={index}
                className="bg-blue-50 border border-blue-200 rounded-lg p-3"
              >
                <div className="flex items-start gap-3">
                  <div className="flex-shrink-0 w-6 h-6 bg-blue-600 text-white text-xs font-bold rounded-full flex items-center justify-center">
                    {index + 1}
                  </div>
                  <div className="flex-1 text-sm text-gray-800">
                    {renderGeneratedTask(task)}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Task Generation LLM Calls */}
      {llmCalls && llmCalls.length > 0 && (
        <div>
          <div className="text-sm font-medium text-gray-700 mb-3">
            Task Generation LLM Calls ({llmCalls.length})
          </div>
          <div className="space-y-3">
            {llmCalls.map((call, idx) => (
              <div key={call.tool_call_id || idx} className="border rounded p-3">
                <ContextualLLMCall llmCall={call} context="task_generation" />
              </div>
            ))}
          </div>
        </div>
      )}
      {/* Backward compatibility: single call field */}
      {!llmCalls && singleCall && (
        <div>
          <div className="text-sm font-medium text-gray-700 mb-3">Task Generation LLM Call</div>
          <ContextualLLMCall llmCall={singleCall} context="task_generation" />
        </div>
      )}

      {/* Additional Information (collapsed by default) */}
      {(taskGeneration.tool_output || taskGeneration.current_task_description) && (
        <details className="border rounded-lg">
          <summary className="px-4 py-3 bg-gray-50 cursor-pointer text-sm font-medium text-gray-700 hover:bg-gray-100">
            Additional Information
          </summary>
          <div className="p-4 space-y-3">
            {taskGeneration.current_task_description && (
              <div>
                <div className="text-sm font-medium text-gray-700 mb-2">Current Task Description</div>
                <div className="text-sm text-gray-800 bg-gray-50 p-3 rounded">
                  {taskGeneration.current_task_description}
                </div>
              </div>
            )}
            
            {taskGeneration.tool_output && (
              <div>
                <div className="text-sm font-medium text-gray-700 mb-2">Tool Output</div>
                <pre className="text-xs text-gray-700 bg-gray-50 p-3 rounded border overflow-x-auto">
                  {JSON.stringify(taskGeneration.tool_output, null, 2)}
                </pre>
              </div>
            )}
          </div>
        </details>
      )}

      {/* Error Display */}
      {taskGeneration.error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-3">
          <div className="text-red-700 text-sm font-medium mb-1">Task Generation Error</div>
          <div className="text-red-600 text-sm">{taskGeneration.error}</div>
        </div>
      )}
    </div>
  );
};
