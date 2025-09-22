import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render } from '@testing-library/react';
import { Timeline } from '../Timeline';
import type { TraceSession } from '../../../types/trace';

// Mock data for testing
const mockTraceWithPendingTasks: TraceSession = {
  session_id: 'test-session',
  start_time: '2023-01-01T10:00:00Z',
  end_time: '2023-01-01T10:30:00Z',
  initial_task_description: 'Test task',
  final_status: 'completed',
  engine_snapshots: {
    start: {
      task_stack: [],
      context: {},
      task_execution_counter: 0
    },
    end: {
      task_stack: [
        'First pending task description',
        'Second pending task description',
        'Third pending task that is currently executing'
      ],
      context: {},
      task_execution_counter: 3
    }
  },
  task_executions: [
    {
      task_execution_id: 'task-1',
      task_execution_counter: 1,
      task_description: 'Completed task 1',
      start_time: '2023-01-01T10:00:00Z',
      end_time: '2023-01-01T10:10:00Z',
      status: 'completed',
      error: null,
      engine_state_before: {
        task_stack: [],
        context: {},
        task_execution_counter: 0
      },
      phases: {}
    },
    {
      task_execution_id: 'task-2',
      task_execution_counter: 2,
      task_description: 'Completed task 2',
      start_time: '2023-01-01T10:10:00Z',
      end_time: '2023-01-01T10:20:00Z',
      status: 'completed',
      error: null,
      engine_state_before: {
        task_stack: [],
        context: {},
        task_execution_counter: 1
      },
      phases: {}
    }
  ]
};

const mockTraceWithoutPendingTasks: TraceSession = {
  ...mockTraceWithPendingTasks,
  engine_snapshots: {
    start: {
      task_stack: [],
      context: {},
      task_execution_counter: 0
    },
    end: {
      task_stack: [],
      context: {},
      task_execution_counter: 2
    }
  }
};

const mockTraceOnlyPendingTasks: TraceSession = {
  ...mockTraceWithPendingTasks,
  task_executions: [],
  engine_snapshots: {
    start: {
      task_stack: [],
      context: {},
      task_execution_counter: 0
    },
    end: {
      task_stack: [
        'Only pending task 1',
        'Only pending task 2 - currently executing'
      ],
      context: {},
      task_execution_counter: 0
    }
  }
};

describe('Timeline with Pending Tasks', () => {
  const mockOnTaskClick = vi.fn();

  beforeEach(() => {
    mockOnTaskClick.mockClear();
  });

  it('should display executed tasks and pending tasks together', () => {
  const { getByText } = render(
      <Timeline
        trace={mockTraceWithPendingTasks}
        onTaskClick={mockOnTaskClick}
        isLoading={false}
      />
    );
  expect(getByText('Completed task 1')).toBeInTheDocument();
  expect(getByText('Completed task 2')).toBeInTheDocument();
  expect(getByText(/First pending task description/)).toBeInTheDocument();
  expect(getByText(/Second pending task description/)).toBeInTheDocument();
  expect(getByText(/Third pending task that is currently executing/)).toBeInTheDocument();
  });

  it('should mark the last pending task as currently executing', () => {
  const { getAllByText } = render(
      <Timeline
        trace={mockTraceWithPendingTasks}
        onTaskClick={mockOnTaskClick}
        isLoading={false}
      />
    );
  const currentlyExecutingBadges = getAllByText('currently executing');
    expect(currentlyExecutingBadges).toHaveLength(1);
  const notStartedBadges = getAllByText('not started');
    expect(notStartedBadges).toHaveLength(2);
  });

  it('should show pending tasks count in header', () => {
  const { getByText } = render(
      <Timeline
        trace={mockTraceWithPendingTasks}
        onTaskClick={mockOnTaskClick}
        isLoading={false}
      />
    );
  expect(getByText('2 tasks executed')).toBeInTheDocument();
  expect(getByText('• 3 pending tasks')).toBeInTheDocument();
  });

  it('should display only pending tasks when no executions exist', () => {
  const { getByText } = render(
      <Timeline
        trace={mockTraceOnlyPendingTasks}
        onTaskClick={mockOnTaskClick}
        isLoading={false}
      />
    );
  expect(getByText('No tasks executed yet')).toBeInTheDocument();
  expect(getByText('• 2 pending tasks')).toBeInTheDocument();
  expect(getByText(/Only pending task 1/)).toBeInTheDocument();
  expect(getByText(/Only pending task 2 - currently executing/)).toBeInTheDocument();
  });

  it('should work normally when no pending tasks exist', () => {
  const { getByText, queryByText } = render(
      <Timeline
        trace={mockTraceWithoutPendingTasks}
        onTaskClick={mockOnTaskClick}
        isLoading={false}
      />
    );
  expect(getByText('2 tasks executed')).toBeInTheDocument();
  expect(queryByText('pending task')).not.toBeInTheDocument();
  });

  it('should show orange styling for currently executing task', () => {
    const { container } = render(
      <Timeline
        trace={mockTraceWithPendingTasks}
        onTaskClick={mockOnTaskClick}
        isLoading={false}
      />
    );

    // Check for orange border styling on currently executing task
    const orangeElements = container.querySelectorAll('.border-orange-400');
    expect(orangeElements.length).toBeGreaterThan(0);
  });

  it('should handle task truncation for long descriptions', () => {
    const longTaskTrace: TraceSession = {
      ...mockTraceWithPendingTasks,
      engine_snapshots: {
        ...mockTraceWithPendingTasks.engine_snapshots,
        end: {
          ...mockTraceWithPendingTasks.engine_snapshots.end!,
          task_stack: [
            'This is a very long task description that should be truncated when displayed in the timeline to ensure the UI remains clean and readable for users while still providing access to the full description through expansion'
          ]
        }
      }
    };

  const { getByText } = render(
      <Timeline
        trace={longTaskTrace}
        onTaskClick={mockOnTaskClick}
        isLoading={false}
      />
    );

    // Should show truncated text with ellipsis
  expect(getByText(/This is a very long task description that should be truncated when displayed in the timeline to ensure the UI remains clean.../)).toBeInTheDocument();
  expect(getByText('Show full description')).toBeInTheDocument();
  });
});
