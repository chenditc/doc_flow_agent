import React from 'react';
import type { TaskCreationPhase } from '../../types/trace';
import { InputFieldInspector } from './InputFieldInspector';
import { InfoIconWithTooltip } from '../common/Tooltip';

interface TaskCreationPhaseViewerProps {
  phaseData: TaskCreationPhase;
}

export const TaskCreationPhaseViewer: React.FC<TaskCreationPhaseViewerProps> = ({ 
  phaseData 
}) => {
  const { 
    sop_document, 
    json_path_generation, 
    created_task, 
    error 
  } = phaseData;

  return (
    <div className="space-y-6">

      {/* Error Display */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <div className="flex items-start gap-3">
            <svg className="h-6 w-6 text-red-500 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <div>
              <h4 className="text-lg font-medium text-red-900 mb-1">Phase Error</h4>
              <p className="text-red-700">{error}</p>
            </div>
          </div>
        </div>
      )}

      {/* SOP Document Summary */}
      <div className="bg-white border rounded-lg shadow-sm">
        <div className="px-4 py-3 border-b bg-gray-50 rounded-t-lg">
          <h4 className="font-medium text-gray-900">SOP Document Used</h4>
        </div>
        <div className="p-4">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <div>
              <label className="text-sm font-medium text-gray-700">Document ID</label>
              <div className="mt-1 p-2 bg-gray-50 border rounded text-sm font-mono">
                {sop_document.doc_id}
              </div>
            </div>
            <div>
              <label className="text-sm font-medium text-gray-700">Description</label>
              <div className="mt-1 p-2 bg-gray-50 border rounded text-sm">
                {sop_document.description}
              </div>
            </div>
          </div>
          
          <div className="mt-4">
            <label className="text-sm font-medium text-gray-700">Required Input Fields</label>
            <div className="mt-1 p-3 bg-gray-50 border rounded">
              {Object.keys(sop_document.input_description).length > 0 ? (
                <div className="space-y-2">
                  {Object.entries(sop_document.input_description).map(([field, desc]) => (
                    <div key={field} className="flex items-start gap-3 text-sm">
                      <span className="font-mono font-medium text-blue-600">{field}:</span>
                      <span className="text-gray-700">{desc}</span>
                    </div>
                  ))}
                </div>
              ) : (
                <span className="text-gray-500 text-sm">No input fields required</span>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Input Field Extraction */}
      {Object.keys(json_path_generation).length > 0 && (
        <div className="space-y-4">
          <div className="flex items-center gap-2">
            <svg className="h-5 w-5 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v10a2 2 0 002 2h8a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01" />
            </svg>
            <h4 className="text-lg font-medium text-gray-900">
              Input Field Extraction ({Object.keys(json_path_generation).length} fields)
            </h4>
            <InfoIconWithTooltip 
              tooltip="This phase extracts input values from context and creates an executable task based on the selected SOP document."
            />
          </div>
          
          <div className="space-y-4">
            {Object.entries(json_path_generation).map(([fieldKey, fieldData]) => (
              <InputFieldInspector
                key={fieldKey}
                fieldName={fieldData.field_name || fieldKey}
                description={fieldData.description || sop_document.input_description[fieldKey] || ''}
                jsonPathGeneration={fieldData}
                contextData={getRelevantContextData(fieldData)}
              />
            ))}
          </div>
        </div>
      )}

      {/* Created Task Summary */}
      <div className="bg-white border rounded-lg shadow-sm">
        <div className="px-4 py-3 border-b bg-gray-50 rounded-t-lg">
          <h4 className="font-medium text-gray-900">Created Task</h4>
        </div>
        <div className="p-4">
          <div className="space-y-4">
            <div>
              <label className="text-sm font-medium text-gray-700">Task ID</label>
              <div className="mt-1 p-2 bg-gray-50 border rounded text-sm font-mono">
                {created_task.task_id}
              </div>
            </div>
            
            <div>
              <label className="text-sm font-medium text-gray-700">Description</label>
              <div className="mt-1 p-2 bg-gray-50 border rounded text-sm">
                {created_task.description}
              </div>
            </div>

            <div>
              <label className="text-sm font-medium text-gray-700">Tool Configuration</label>
              <div className="mt-1 p-3 bg-gray-50 border rounded">
                <div className="text-sm space-y-2">
                  <div>
                    <span className="font-medium text-gray-700">Tool ID:</span>
                    <span className="ml-2 font-mono text-blue-600">{created_task.tool.tool_id}</span>
                  </div>
                  {created_task.tool.parameters && (
                    <div>
                      <span className="font-medium text-gray-700">Parameters:</span>
                      <pre className="mt-1 text-xs bg-white border rounded p-2 overflow-x-auto">
                        {JSON.stringify(created_task.tool.parameters, null, 2)}
                      </pre>
                    </div>
                  )}
                </div>
              </div>
            </div>

            <div>
              <label className="text-sm font-medium text-gray-700">Input Mapping</label>
              <div className="mt-1 p-3 bg-gray-50 border rounded">
                {Object.keys(created_task.input_json_path).length > 0 ? (
                  <div className="space-y-2">
                    {Object.entries(created_task.input_json_path).map(([param, path]) => (
                      <div key={param} className="flex items-center gap-3 text-sm">
                        <span className="font-mono font-medium text-purple-600">{param}:</span>
                        <code className="bg-white border rounded px-2 py-1 text-xs font-mono">
                          {path}
                        </code>
                      </div>
                    ))}
                  </div>
                ) : (
                  <span className="text-gray-500 text-sm">No input mappings</span>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

// Helper function to extract relevant context data for a field
function getRelevantContextData(_fieldData: any): Record<string, any> {
  // This would ideally come from the engine state, but for now we'll return a simplified version
  // In a real implementation, this would extract the specific context data that was available
  // during the field extraction process
  
  const mockContext: Record<string, any> = {
    current_task: "Task description from context",
    // Add other relevant context fields based on the field data
  };

  // If we have information about what context was used, we could filter it here
  // For now, return a basic context structure
  return mockContext;
}
