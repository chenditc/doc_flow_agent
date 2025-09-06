/**
 * Formatting utilities for Doc Flow Trace Viewer
 * TypeScript refactored version with enhanced type safety
 */

import type { TaskExecution, PhaseStatus } from '../types';

/**
 * Safely escape HTML content to prevent XSS
 */
export const escapeHtml = (unsafe: any): string => {
  if (!unsafe) return '';

  // Convert to string if not already a string
  const str = typeof unsafe === 'string' ? unsafe : String(unsafe);

  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
};

/**
 * Format timestamp for display
 */
export const formatTime = (timestamp: string | null): string => {
  if (!timestamp) return 'N/A';
  
  try {
    return new Date(timestamp).toLocaleTimeString();
  } catch (error) {
    return 'Invalid time';
  }
};

/**
 * Format timestamp as full date and time
 */
export const formatDateTime = (timestamp: string | null): string => {
  if (!timestamp) return 'N/A';
  
  try {
    return new Date(timestamp).toLocaleString();
  } catch (error) {
    return 'Invalid date';
  }
};

/**
 * Calculate duration between start and end times
 */
export const calculateDuration = (startTime: string | null, endTime: string | null): string => {
  if (!startTime || !endTime) return 'N/A';

  try {
    const start = new Date(startTime);
    const end = new Date(endTime);
    const diffMs = end.getTime() - start.getTime();
    
    if (diffMs < 0) return 'Invalid duration';
    
    return formatDuration(diffMs);
  } catch (error) {
    return 'Invalid duration';
  }
};

/**
 * Format milliseconds as human-readable duration
 */
export const formatDuration = (durationMs: number): string => {
  if (durationMs < 1000) {
    return `${Math.round(durationMs)}ms`;
  }
  
  const diffSec = Math.round(durationMs / 1000);
  
  if (diffSec < 60) {
    return `${diffSec}s`;
  } else if (diffSec < 3600) {
    const minutes = Math.floor(diffSec / 60);
    const seconds = diffSec % 60;
    return `${minutes}m ${seconds}s`;
  } else {
    const hours = Math.floor(diffSec / 3600);
    const minutes = Math.floor((diffSec % 3600) / 60);
    const seconds = diffSec % 60;
    return `${hours}h ${minutes}m ${seconds}s`;
  }
};

/**
 * Extract task output from trace data
 */
export const extractTaskOutput = (task: TaskExecution): string => {
  // First, try to get from engine_state_after.context.last_task_output
  if (
    task.engine_state_after?.context?.last_task_output
  ) {
    const output = task.engine_state_after.context.last_task_output;
    return formatOutput(output);
  }

  // Look for context_update phase with updated_paths
  if (task.phases?.context_update) {
    // Try to find updated context values
    if (task.engine_state_after?.context) {
      const context = task.engine_state_after.context;
      
      // Look for any meaningful output in context
      for (const [key, value] of Object.entries(context)) {
        if (key.includes('output') || key.includes('result') || key === 'last_task_output') {
          return formatOutput(value);
        }
      }
    }
  }

  // Look in tool execution output
  if (task.phases?.task_execution?.tool_execution?.output) {
    return formatOutput(task.phases.task_execution.tool_execution.output);
  }

  // Fallback: if there's an error, show that
  if (task.error) {
    return `Error: ${task.error}`;
  }

  // Default fallback - show first meaningful context value
  if (task.engine_state_after?.context) {
    const contextValues = Object.entries(task.engine_state_after.context);
    for (const [key, value] of contextValues) {
      if (typeof value === 'string' && value.length > 10) {
        return value;
      } else if (typeof value === 'object' && value !== null && key.includes('output')) {
        return formatOutput(value);
      }
    }
  }

  return 'No output available';
};

/**
 * Format output data consistently
 */
const formatOutput = (output: any): string => {
  if (typeof output === 'string') {
    try {
      // Try to parse JSON string
      const parsed = JSON.parse(output);
      return formatOutput(parsed);
    } catch {
      // Not JSON, return as-is
      return output;
    }
  } else if (typeof output === 'object' && output !== null) {
    // Handle structured output (e.g., {stdout, stderr})
    if (output.stdout || output.stderr) {
      let result = '';
      if (output.stdout) result += output.stdout;
      if (output.stderr) {
        result += (result ? '\n--- STDERR ---\n' : '') + output.stderr;
      }
      return result || 'No output';
    } else {
      // For other objects, stringify them
      return JSON.stringify(output, null, 2);
    }
  }
  
  return String(output || '');
};

/**
 * Extract phases from trace data
 */
export const extractPhases = (task: TaskExecution): Array<{
  name: string;
  displayName: string;
  status: PhaseStatus;
  start_time: string | null;
  end_time: string | null;
  duration: string;
  error?: string | null;
}> => {
  if (!task.phases) return [];

  return Object.entries(task.phases).map(([name, phaseData]) => ({
    name,
    displayName: name.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()),
    status: phaseData?.status || 'error',
    start_time: phaseData?.start_time || null,
    end_time: phaseData?.end_time || null,
    duration: calculateDuration(phaseData?.start_time || null, phaseData?.end_time || null),
    error: phaseData?.error || null,
  }));
};

/**
 * Truncate long text with ellipsis
 */
export const truncateText = (text: string | null, maxLength = 500): string => {
  if (!text || typeof text !== 'string') return '';
  if (text.length <= maxLength) return text;
  return text.substring(0, maxLength) + '...';
};

/**
 * Format status with appropriate styling classes
 */
export const getStatusColor = (status: PhaseStatus): string => {
  switch (status) {
    case 'completed':
      return 'text-green-600 bg-green-100';
    case 'started':
      return 'text-blue-600 bg-blue-100 animate-pulse';
    case 'failed':
    case 'interrupted':
      return 'text-red-600 bg-red-100';
    case 'retrying':
      return 'text-orange-600 bg-orange-100';
    default:
      return 'text-gray-600 bg-gray-100';
  }
};

/**
 * Format status text for display
 */
export const formatStatus = (status: PhaseStatus): string => {
  return status.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
};

/**
 * Extract LLM calls from task data
 */
export const extractLLMCalls = (task: TaskExecution): Array<{
  id: string;
  step: string;
  model: string;
  prompt: string;
  response: string;
  start_time: string;
  end_time: string;
  duration: string;
  token_usage: any;
}> => {
  const llmCalls: any[] = [];

  // Helper to add LLM call if it exists
  const addLLMCall = (call: any, phase: string) => {
    if (call && call.tool_call_id) {
      llmCalls.push({
        id: call.tool_call_id,
        step: call.step || phase,
        model: call.model || 'Unknown',
        prompt: call.prompt || '',
        response: call.response || '',
        start_time: call.start_time || '',
        end_time: call.end_time || '',
        duration: calculateDuration(call.start_time, call.end_time),
        token_usage: call.token_usage,
      });
    }
  };

  // Check SOP resolution phase
  if (task.phases?.sop_resolution?.document_selection) {
    const ds: any = task.phases.sop_resolution.document_selection;
    if (ds.llm_calls && Array.isArray(ds.llm_calls)) {
      ds.llm_calls.forEach((c: any) => addLLMCall(c, 'SOP Resolution'));
    } else if (ds.validation_call) {
      addLLMCall(ds.validation_call, 'SOP Resolution');
    }
  }

  // Check task creation phase
  if (task.phases?.task_creation?.input_field_extractions) {
    Object.entries(task.phases.task_creation.input_field_extractions).forEach(([field, extraction]: [string, any]) => {
      if (extraction?.context_analysis_call) {
        addLLMCall(extraction.context_analysis_call, `Task Creation - ${field} (Analysis)`);
      }
      if (extraction?.extraction_code_generation_call) {
        addLLMCall(extraction.extraction_code_generation_call, `Task Creation - ${field} (Code Gen)`);
      }
    });
  }

  // Check task creation output path generation
  if (task.phases?.task_creation?.output_path_generation) {
    const opg: any = task.phases.task_creation.output_path_generation;
    if (opg.llm_calls && Array.isArray(opg.llm_calls)) {
      opg.llm_calls.forEach((c: any) => addLLMCall(c, 'Task Creation - Output Path'));
    } else if (opg.path_generation_call) {
      addLLMCall(opg.path_generation_call, 'Task Creation - Output Path');
    }
  }

  // Check task execution phase
  if (task.phases?.task_execution?.output_path_generation) {
    const opgExec: any = task.phases.task_execution.output_path_generation;
    if (opgExec.llm_calls && Array.isArray(opgExec.llm_calls)) {
      opgExec.llm_calls.forEach((c: any) => addLLMCall(c, 'Task Execution - Output Path'));
    } else if (opgExec.path_generation_call) {
      addLLMCall(opgExec.path_generation_call, 'Task Execution - Output Path');
    }
  }

  // Check new task generation phase
  if (task.phases?.new_task_generation?.task_generation) {
    const ntg: any = task.phases.new_task_generation.task_generation;
    if (ntg.llm_calls && Array.isArray(ntg.llm_calls)) {
      ntg.llm_calls.forEach((c: any) => addLLMCall(c, 'New Task Generation'));
    } else if (ntg.task_generation_call) {
      addLLMCall(ntg.task_generation_call, 'New Task Generation');
    }
  }

  return llmCalls;
};

/**
 * Get relative time string (e.g., "2 minutes ago")
 */
export const getRelativeTime = (timestamp: string | null): string => {
  if (!timestamp) return 'Unknown';

  try {
    const now = new Date();
    const past = new Date(timestamp);
    const diffMs = now.getTime() - past.getTime();

    if (diffMs < 60000) {
      return 'Just now';
    } else if (diffMs < 3600000) {
      const minutes = Math.floor(diffMs / 60000);
      return `${minutes} minute${minutes > 1 ? 's' : ''} ago`;
    } else if (diffMs < 86400000) {
      const hours = Math.floor(diffMs / 3600000);
      return `${hours} hour${hours > 1 ? 's' : ''} ago`;
    } else {
      const days = Math.floor(diffMs / 86400000);
      return `${days} day${days > 1 ? 's' : ''} ago`;
    }
  } catch (error) {
    return 'Invalid time';
  }
};
