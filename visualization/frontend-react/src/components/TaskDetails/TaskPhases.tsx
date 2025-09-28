import React, { useState } from 'react';
import type { TaskExecution, TaskPhases as TaskPhasesType, TaskExecutionPhase, LLMCall, ContextUpdatePhase, NewTaskGenerationPhase, SubtreeCompactionPhase } from '../../types/trace';
import { SOPResolutionViewer } from '../SOPResolution/SOPResolutionViewer';
import { TaskCreationPhaseViewer } from '../enhanced/TaskCreationPhaseViewer';
import { NewTaskGenerationViewer } from '../enhanced/NewTaskGenerationViewer';
import { SubtreeCompactionViewer } from '../enhanced/SubtreeCompactionViewer';
import { ContextualLLMCall } from '../enhanced/ContextualLLMCall';
import { ParameterCards } from './ParameterCards';
import { ContextUpdateViewer } from './ContextUpdateViewer';
import { JsonViewer as NiceJsonViewer } from '../common/JsonViewer';

interface TaskPhasesProps {
  task: TaskExecution;
}

interface CollapsibleSectionProps {
  title: string;
  children: React.ReactNode;
  defaultExpanded?: boolean;
  statusBadge?: React.ReactNode;
  rightContent?: React.ReactNode;
}

const CollapsibleSection: React.FC<CollapsibleSectionProps> = ({ 
  title, 
  children, 
  defaultExpanded = false,
  statusBadge,
  rightContent
}) => {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);

  return (
    <div className="border rounded-md">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full px-4 py-3 text-left bg-gray-50 hover:bg-gray-100 focus:outline-none focus:bg-gray-100 transition-colors border-b border-gray-200 rounded-t-md"
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="font-medium text-gray-900">{title}</span>
            {statusBadge}
          </div>
          <div className="flex items-center gap-3">
            {rightContent}
            <svg
              className={`h-5 w-5 text-gray-500 transition-transform ${isExpanded ? 'rotate-180' : ''}`}
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          </div>
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

export const TaskPhases: React.FC<TaskPhasesProps> = ({ task }) => {
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
    } catch (error) {
      return 'Invalid duration';
    }
  };

  const getStatusBadgeColor = (status: string): string => {
    switch (status) {
      case 'completed':
        return 'bg-green-100 text-green-800';
      case 'failed':
        return 'bg-red-100 text-red-800';
      case 'started':
        return 'bg-blue-100 text-blue-800';
      case 'interrupted':
        return 'bg-yellow-100 text-yellow-800';
      case 'retrying':
        return 'bg-orange-100 text-orange-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const formatPhaseName = (phaseName: string): string => {
    return phaseName
      .replace(/_/g, ' ')
      .replace(/\b\w/g, l => l.toUpperCase());
  };

  const stripMetaFields = (phaseData: any) => {
    if (!phaseData || typeof phaseData !== 'object') return {};
    
    const { start_time, end_time, status, ...rest } = phaseData;
    return rest;
  };

  const phases = task.phases || {};
  const phaseNames = Object.keys(phases);

  if (phaseNames.length === 0) {
    return (
      <div className="text-center py-8">
        <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        <h3 className="mt-4 text-sm font-medium text-gray-900">No phase information</h3>
        <p className="mt-2 text-sm text-gray-500">
          This task execution doesn't have detailed phase information available.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <h3 className="text-lg font-medium text-gray-900">Execution Phases</h3>
      
      <div className="space-y-3">
        {phaseNames.map((phaseName, index) => {
          const phaseData = phases[phaseName as keyof TaskPhasesType];
          if (!phaseData) return null;

          // Create a nicely formatted number index
          const phaseIndex = index + 1;

          // Special handling for SOP resolution phase
          if (phaseName === 'sop_resolution' && 'input' in phaseData) {
            // Try multiple ways to get the selected document ID
            let sopDoc = '';
            
            // Primary path: document_selection.selected_doc_id
            if (phaseData.document_selection?.selected_doc_id) {
              sopDoc = phaseData.document_selection.selected_doc_id;
            }
            // Fallback: check if there's a selected_doc_id directly in phaseData
            else if ((phaseData as any).selected_doc_id) {
              sopDoc = (phaseData as any).selected_doc_id;
            }
            // Another fallback: check loaded_document.doc_id
            else if (phaseData.document_selection?.loaded_document?.doc_id) {
              sopDoc = phaseData.document_selection.loaded_document.doc_id;
            }
            
            const sopDocSuffix = sopDoc ? ` (${sopDoc})` : '';
            
            const statusBadge = (
              <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getStatusBadgeColor(phaseData.status)}`}>
                {phaseData.status}
              </span>
            );

            const timingInfo = (
              <div className="text-sm text-gray-500">
                {formatTime(phaseData.start_time)} - {formatTime(phaseData.end_time)} 
                ({calculateDuration(phaseData.start_time, phaseData.end_time)})
              </div>
            );
            
            return (
              <CollapsibleSection 
                key={phaseName}
                title={`${phaseIndex}. SOP Resolution${sopDocSuffix}`}
                defaultExpanded={false}
                statusBadge={statusBadge}
                rightContent={timingInfo}
              >
                <SOPResolutionViewer phaseData={phaseData} />
              </CollapsibleSection>
            );
          }

          // Special handling for task creation phase
          if (phaseName === 'task_creation' && 'sop_document' in phaseData) {
            const inputFieldCount = Object.keys(phaseData.input_field_extractions || {}).length;
            const batchFieldCount = phaseData.batch_input_field_extraction 
              ? Object.keys(phaseData.batch_input_field_extraction.input_descriptions || {}).length 
              : 0;
            
            let inputFieldSuffix = '';
            if (batchFieldCount > 0 && inputFieldCount > 0) {
              inputFieldSuffix = ` (${batchFieldCount} batch + ${inputFieldCount} individual fields)`;
            } else if (batchFieldCount > 0) {
              inputFieldSuffix = ` (${batchFieldCount} fields via batch)`;
            } else if (inputFieldCount > 0) {
              inputFieldSuffix = ` (${inputFieldCount} fields)`;
            }
            
            const statusBadge = (
              <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getStatusBadgeColor(phaseData.status)}`}>
                {phaseData.status}
              </span>
            );

            const timingInfo = (
              <div className="text-sm text-gray-500">
                {formatTime(phaseData.start_time)} - {formatTime(phaseData.end_time)} 
                ({calculateDuration(phaseData.start_time, phaseData.end_time)})
              </div>
            );
            
            return (
              <CollapsibleSection 
                key={phaseName}
                title={`${phaseIndex}. Task Creation${inputFieldSuffix}`}
                defaultExpanded={false}
                statusBadge={statusBadge}
                rightContent={timingInfo}
              >
                <TaskCreationPhaseViewer phaseData={phaseData} />
              </CollapsibleSection>
            );
          }

          // Special handling for new task generation phase
          if (phaseName === 'new_task_generation' && 'task_generation' in phaseData) {
            const newTaskGenPhase = phaseData as NewTaskGenerationPhase;
            const taskCount = newTaskGenPhase.task_generation?.generated_tasks?.length || 0;
            const titleSuffix = ` (${taskCount} task${taskCount === 1 ? '' : 's'} generated)`;
            
            const statusBadge = (
              <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getStatusBadgeColor(newTaskGenPhase.status)}`}>
                {newTaskGenPhase.status}
              </span>
            );

            const timingInfo = (
              <div className="text-sm text-gray-500">
                {formatTime(newTaskGenPhase.start_time)} - {formatTime(newTaskGenPhase.end_time)} 
                ({calculateDuration(newTaskGenPhase.start_time, newTaskGenPhase.end_time)})
              </div>
            );
            
            return (
              <CollapsibleSection 
                key={phaseName}
                title={`${phaseIndex}. New Task Generation${titleSuffix}`}
                defaultExpanded={false}
                statusBadge={statusBadge}
                rightContent={timingInfo}
              >
                <NewTaskGenerationViewer phaseData={newTaskGenPhase} />
              </CollapsibleSection>
            );
          }

          // Special handling for subtree compaction phase
          if (phaseName === 'subtree_compaction' && 'root_task_id' in phaseData) {
            const compactionPhase = phaseData as SubtreeCompactionPhase;
            const outputCount = Object.keys(compactionPhase.aggregated_outputs || {}).length;
            const taskCount = compactionPhase.subtree_task_ids?.length || 0;
            // Optional generated tasks summary (just a count)
            const generatedTasks: any[] = (compactionPhase as any).generated_tasks || [];
            const generatedCount = generatedTasks.length;
            const generatedPart = generatedCount > 0 ? `, ${generatedCount} generated` : '';
            const titleSuffix = ` (${outputCount} output${outputCount === 1 ? '' : 's'}, ${taskCount} compact task${taskCount === 1 ? '' : 's'}${generatedPart})`;
            
            const statusBadge = (
              <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getStatusBadgeColor(compactionPhase.status)}`}>
                {compactionPhase.status}
              </span>
            );

            const timingInfo = (
              <div className="text-sm text-gray-500">
                {formatTime(compactionPhase.start_time)} - {formatTime(compactionPhase.end_time)} 
                ({calculateDuration(compactionPhase.start_time, compactionPhase.end_time)})
              </div>
            );
            
            return (
              <CollapsibleSection 
                key={phaseName}
                title={`${phaseIndex}. Subtree Compaction${titleSuffix}`}
                defaultExpanded={false}
                statusBadge={statusBadge}
                rightContent={timingInfo}
              >
                <SubtreeCompactionViewer phaseData={compactionPhase} />
              </CollapsibleSection>
            );
          }

          // Special handling for context update phase
          if (phaseName === 'context_update' && 'context_before' in phaseData) {
            const contextPhase = phaseData as ContextUpdatePhase;

            const statusBadge = (
              <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getStatusBadgeColor(contextPhase.status)}`}>
                {contextPhase.status}
              </span>
            );

            const timingInfo = (
              <div className="text-sm text-gray-500">
                {formatTime(contextPhase.start_time)} - {formatTime(contextPhase.end_time)} 
                ({calculateDuration(contextPhase.start_time, contextPhase.end_time)})
              </div>
            );

            return (
              <CollapsibleSection 
                key={phaseName}
                title={`${phaseIndex}. Context Update`}
                defaultExpanded={false}
                statusBadge={statusBadge}
                rightContent={timingInfo}
              >
                <ContextUpdateViewer phaseData={contextPhase} />
              </CollapsibleSection>
            );
          }

          // Special handling for task execution phase - structured display
          if (phaseName === 'task_execution') {
            const execPhase = phaseData as TaskExecutionPhase;
            const toolId = execPhase.task?.tool?.tool_id || execPhase.tool_execution?.tool_id || '';
            const toolSuffix = toolId ? ` (${toolId})` : '';

            const statusBadge = (
              <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getStatusBadgeColor(execPhase.status)}`}>
                {execPhase.status}
              </span>
            );

            const timingInfo = (
              <div className="text-sm text-gray-500">
                {formatTime(execPhase.start_time)} - {formatTime(execPhase.end_time)} 
                ({calculateDuration(execPhase.start_time, execPhase.end_time)})
              </div>
            );

            return (
              <CollapsibleSection 
                key={phaseName} 
                title={`${phaseIndex}. Task Execution${toolSuffix}`} 
                defaultExpanded={false}
                statusBadge={statusBadge}
                rightContent={timingInfo}
              >
                <div className="space-y-4">
                  {/* Task Tool Info (collapsed by default) */}
                  {execPhase.task && (
                    <CollapsibleSection 
                      title={`Tool Configuration - ${execPhase.task.tool?.tool_id || 'Unknown Tool'}`} 
                      defaultExpanded={false}
                    >
                      <div className="text-sm space-y-4">
                        <div>
                          <span className="font-medium text-gray-700">Tool ID:</span>
                          <span className="ml-2 font-mono text-blue-600">{execPhase.task.tool?.tool_id || 'N/A'}</span>
                        </div>
                        <div>
                          <div className="font-medium text-gray-700 mb-3">Parameters:</div>
                          <ParameterCards parameters={execPhase.task.tool?.parameters || {}} />
                        </div>
                      </div>
                    </CollapsibleSection>
                  )}

                  {/* Tool Execution: if LLM then render LLM component, otherwise JSON */}
                  <div>
                    {(() => {
                      let len: number | null = null;
                      if (execPhase.tool_execution) {
                        try { len = JSON.stringify(execPhase.tool_execution).length; } catch { len = null; }
                      }
                      return <div className="text-sm font-medium text-gray-700 mb-2">Tool Execution{len !== null ? ` (${len.toLocaleString()} chars)` : ''}</div>;
                    })()}
                     {execPhase.tool_execution ? (
                       execPhase.tool_execution.tool_id === 'LLM' || execPhase.task?.tool?.tool_id === 'LLM' ? (
                         (() => {
                           // Map ToolExecution to a temporary LLMCall shape for display
                           const toolExec = execPhase.tool_execution as any;
                           const syntheticLLM: LLMCall = {
                             tool_call_id: toolExec.tool_call_id || 'unknown',
                             prompt: (toolExec.parameters && (toolExec.parameters.prompt || toolExec.parameters['prompt'])) || '',
                             response: toolExec.output.content,
                             start_time: toolExec.start_time || execPhase.start_time || '',
                             end_time: toolExec.end_time || execPhase.end_time || '',
                             model: toolExec.parameters?.model || undefined,
                             token_usage: toolExec.parameters?.token_usage || undefined,
                           };

                           return <ContextualLLMCall 
                             llmCall={syntheticLLM} 
                             context="field_extraction"
                             relatedData={toolExec.parameters}
                           />;
                         })()
                       ) : (
                         <div className="text-xs text-gray-700 bg-gray-50 p-3 rounded border overflow-x-auto">
                           <NiceJsonViewer value={execPhase.tool_execution} label="Tool Execution" collapsed={false} />
                         </div>
                       )
                     ) : (
                       <div className="text-sm text-gray-500">No tool execution recorded</div>
                     )}
                  </div>

                  {/* Nested LLM calls during tool execution */}
                  {execPhase.llm_calls && execPhase.llm_calls.length > 0 && (
                    <div>
                      <div className="text-sm font-medium text-gray-700 mb-2">Nested LLM Calls</div>
                      <div className="space-y-3">
                        {execPhase.llm_calls.map((call, idx) => (
                          <div key={call.tool_call_id || idx} className="border rounded p-3">
                            <ContextualLLMCall 
                              llmCall={call} 
                              context="field_extraction" 
                              relatedData={execPhase.tool_execution?.parameters}
                            />
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Output Path Generation - display prefixed_path and collapsible call details */}
                  {(execPhase.prefixed_path || execPhase.output_path_generation) && (
                    <div>
                      <div className="text-sm font-medium text-gray-700 mb-2">Output Path Generation</div>
                      <div className="p-3 bg-gray-50 border rounded text-sm space-y-2">
                        <div>
                          <span className="font-medium text-gray-700">Prefixed Path:</span>
                          <code className="ml-2 font-mono bg-white px-2 py-1 rounded">{execPhase.prefixed_path || execPhase.output_path_generation?.prefixed_path || 'N/A'}</code>
                        </div>
                        {execPhase.output_path_generation && (
                          <CollapsibleSection title="View Path Generation Calls" defaultExpanded={false}>
                            {((execPhase.output_path_generation as any).llm_calls as any[] | undefined)?.length ? (
                              <div className="space-y-3">
                                {((execPhase.output_path_generation as any).llm_calls as any[]).map((call: any, idx: number) => (
                                  <ContextualLLMCall key={call.tool_call_id || idx} llmCall={call} context="output_generation" />
                                ))}
                              </div>
                            ) : (execPhase.output_path_generation as any).path_generation_call ? (
                              <ContextualLLMCall llmCall={(execPhase.output_path_generation as any).path_generation_call} context="output_generation" />
                            ) : (
                              <div className="text-sm text-gray-500">No path generation call recorded.</div>
                            )}
                          </CollapsibleSection>
                        )}
                      </div>
                    </div>
                  )}

                  {/* Phase-level error display */}
                  {execPhase.error && (
                    <div className="bg-red-50 border border-red-200 rounded-lg p-3">
                      <div className="text-red-700 text-sm">{execPhase.error}</div>
                    </div>
                  )}
                </div>
              </CollapsibleSection>
            );
          }

          // Generic phase handling
          const detailsData = stripMetaFields(phaseData);
          const hasDetails = Object.keys(detailsData).length > 0;

          const statusBadge = (
            <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getStatusBadgeColor(phaseData.status)}`}>
              {phaseData.status}
            </span>
          );

          const timingInfo = (
            <div className="text-sm text-gray-500">
              {formatTime(phaseData.start_time)} - {formatTime(phaseData.end_time)} 
              ({calculateDuration(phaseData.start_time, phaseData.end_time)})
            </div>
          );

          if (hasDetails) {
            return (
              <CollapsibleSection 
                key={phaseName}
                title={`${phaseIndex}. ${formatPhaseName(phaseName)}`}
                defaultExpanded={false}
                statusBadge={statusBadge}
                rightContent={timingInfo}
              >
                <div className="text-xs text-gray-700 bg-gray-50 p-3 rounded border overflow-x-auto">
                  <NiceJsonViewer value={detailsData} label={formatPhaseName(phaseName)} collapsed={false} />
                </div>
              </CollapsibleSection>
            );
          } else {
            // If no details, still show the phase header but without expandable content
            return (
              <div key={phaseName} className="border rounded-md">
                <div className="px-4 py-3 bg-gray-50 rounded-md">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <span className="font-medium text-gray-900">{phaseIndex}. {formatPhaseName(phaseName)}</span>
                      {statusBadge}
                    </div>
                    {timingInfo}
                  </div>
                </div>
              </div>
            );
          }
        })}
      </div>
    </div>
  );
};
