import React, { useState } from 'react';
import type { TaskExecution } from '../../types/trace';
import { Modal } from '../common/Modal';
import { TaskSummary } from './TaskSummary';
import { TaskOutput } from './TaskOutput';
import { TaskPhases } from './TaskPhases';

interface TaskDetailsModalProps {
  isOpen: boolean;
  onClose: () => void;
  task: TaskExecution | null;
}

type TabType = 'summary' | 'output' | 'phases';

export const TaskDetailsModal: React.FC<TaskDetailsModalProps> = ({
  isOpen,
  onClose,
  task
}) => {
  const [activeTab, setActiveTab] = useState<TabType>('summary');

  // Reset tab when modal opens with new task
  React.useEffect(() => {
    if (isOpen) {
      setActiveTab('summary');
    }
  }, [isOpen, task]);

  if (!task) {
    return null;
  }

  const tabs: Array<{ id: TabType; label: string; count?: number }> = [
    { id: 'summary', label: 'Summary' },
    { id: 'output', label: 'Output' },
    { 
      id: 'phases', 
      label: 'Phases',
      count: task.phases ? Object.keys(task.phases).length : 0
    }
  ];

  const renderTabContent = () => {
    switch (activeTab) {
      case 'summary':
        return <TaskSummary task={task} />;
      case 'output':
        return <TaskOutput task={task} />;
      case 'phases':
        return <TaskPhases task={task} />;
      default:
        return null;
    }
  };

  const modalTitle = task.task_description || `Task ${task.task_execution_counter}`;

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={modalTitle}
      size="xlarge"
    >
      <div className="flex flex-col h-full">
        {/* Tab Navigation */}
        <div className="border-b border-gray-200 mb-6">
          <nav className="-mb-px flex space-x-8">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`py-2 px-1 border-b-2 font-medium text-sm whitespace-nowrap ${
                  activeTab === tab.id
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                {tab.label}
                {tab.count !== undefined && tab.count > 0 && (
                  <span className="ml-2 inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
                    {tab.count}
                  </span>
                )}
              </button>
            ))}
          </nav>
        </div>

        {/* Tab Content */}
        <div className="flex-1 overflow-y-auto">
          {renderTabContent()}
        </div>
      </div>
    </Modal>
  );
};
