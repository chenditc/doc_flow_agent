import React, { useState } from 'react';
import type { HierarchicalTask } from '../../utils/taskHierarchy';
import type { TaskExecution } from '../../types/trace';
import { TimelineItem } from './TimelineItem';
import { PendingTaskItem } from './PendingTaskItem';
import { ChevronDown, ChevronRight } from 'lucide-react';

interface TaskTreeItemProps {
  task: HierarchicalTask;
  onTaskClick: (task: TaskExecution) => void;
  isNew: boolean;
}

export const TaskTreeItem: React.FC<TaskTreeItemProps> = ({ task, onTaskClick, isNew }) => {
  const [isCollapsed, setIsCollapsed] = useState(false);
  const hasChildren = task.children && task.children.length > 0;

  const handleToggleCollapse = (e: React.MouseEvent) => {
    e.stopPropagation();
    setIsCollapsed(!isCollapsed);
  };

  const handleItemClick = () => {
    if (!task.isPending) {
      onTaskClick(task as TaskExecution);
    }
  };

  // Fixed icon slot width to keep alignment consistent regardless of children
  const ICON_SLOT_WIDTH = 20; // px

  return (
    <div className="w-full">
      <div className="flex items-start w-full">
        {/* Indent gutter based on level */}
        <div style={{ width: `${task.level * ICON_SLOT_WIDTH}px` }} className="flex-shrink-0" />

        {/* Icon slot: chevron or spacer */}
        <div style={{ width: `${ICON_SLOT_WIDTH}px` }} className="flex-shrink-0 flex items-center justify-center">
          {hasChildren ? (
            <button onClick={handleToggleCollapse} className="focus:outline-none">
              {isCollapsed ? <ChevronRight size={16} /> : <ChevronDown size={16} />}
            </button>
          ) : (
            <span style={{ display: 'inline-block', width: 16, height: 16 }} />
          )}
        </div>

        {/* Content */}
        <div className="flex-grow">
          {task.isPending ? (
            <PendingTaskItem taskDescription={task.description} shortName={task.short_name} />
          ) : (
            <TimelineItem
              key={task.task_execution_id}
              item={task as TaskExecution}
              onItemClick={handleItemClick}
              isNew={isNew}
            />
          )}
        </div>
      </div>

      {!isCollapsed && hasChildren && (
        <div className="mt-1">
          {task.children.map(child => (
            <TaskTreeItem
              key={child.task_id}
              task={child}
              onTaskClick={onTaskClick}
              isNew={false}
            />
          ))}
        </div>
      )}
    </div>
  );
};
