import type { TaskExecution } from '../types/trace';

export interface HierarchicalTask extends Partial<TaskExecution> {
  task_id: string;
  description: string;
  // Prefer short name for compact display when available
  short_name?: string;
  parent_task_id?: string | null;
  children: HierarchicalTask[];
  level: number;
  isPending: boolean;
}

export function buildTaskHierarchy(
  executedTasks: TaskExecution[],
  pendingTasks: any[]
): HierarchicalTask[] {
  const taskMap = new Map<string, HierarchicalTask>();
  const rootTasks: HierarchicalTask[] = [];

  // First pass: process executed tasks
  executedTasks.forEach(task => {
    const createdTask = task.phases?.task_creation?.created_task;
    // Prefer explicit task_id on the execution record (new tracer), else created_task.task_id, else fallback to execution id
    const taskId = task.task_id ?? createdTask?.task_id ?? task.task_execution_id;
    taskMap.set(taskId, {
      ...task,
      task_id: taskId,
  description: task.task_description,
  short_name: task.short_name ?? createdTask?.short_name,
  // Use execution-level parent_task_id when available (populated at start), else from created_task
  parent_task_id: task.parent_task_id ?? createdTask?.parent_task_id,
      children: [],
      level: 0,
      isPending: false,
    });
  });

  // Second pass: process pending tasks
  pendingTasks.forEach(pending => {
    if (!taskMap.has(pending.task_id)) {
      taskMap.set(pending.task_id, {
        task_id: pending.task_id,
        description: pending.description,
  short_name: pending.short_name,
        parent_task_id: pending.parent_task_id,
        children: [],
        level: 0,
        isPending: true,
        // Add required fields from TaskExecution with default/empty values
        task_execution_id: pending.task_id, // Use task_id as a fallback
        task_execution_counter: -1,
        task_description: pending.description,
        start_time: new Date().toISOString(),
        end_time: null,
        status: 'running', // Or a new 'pending' status
        error: null,
        engine_state_before: {} as any,
        phases: {},
      });
    }
  });

  // Third pass: build hierarchy
  taskMap.forEach(task => {
    const parentId = task.parent_task_id;
    if (parentId && taskMap.has(parentId)) {
      const parent = taskMap.get(parentId)!;
      parent.children.push(task);
    } else {
      rootTasks.push(task);
    }
  });

  // Fourth pass: set levels and sort
  const setLevels = (tasks: HierarchicalTask[], level: number) => {
    for (const task of tasks) {
      task.level = level;
      if (task.children.length > 0) {
        // Sort children by start time for executed, and by original order for pending
        task.children.sort((a, b) => {
          if (a.isPending && b.isPending) return 0;
          if (a.isPending) return 1;
          if (b.isPending) return -1;
          return new Date(a.start_time!).getTime() - new Date(b.start_time!).getTime();
        });
        setLevels(task.children, level + 1);
      }
    }
  };

  rootTasks.sort((a, b) => {
    if (a.isPending && b.isPending) return 0;
    if (a.isPending) return 1;
    if (b.isPending) return -1;
    return new Date(a.start_time!).getTime() - new Date(b.start_time!).getTime();
  });
  
  setLevels(rootTasks, 0);

  return rootTasks;
}
