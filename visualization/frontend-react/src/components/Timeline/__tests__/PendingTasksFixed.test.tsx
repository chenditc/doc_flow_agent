import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { Timeline } from '../Timeline';
import type { TraceSession } from '../../../types/trace';

// Mock data for testing the corrected logic
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
        'First pending task - should be currently executing',
        'Second pending task - should be not started',
        'Third pending task - should be not started'
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
    }
  ]
};

describe('Timeline with Corrected Pending Tasks Logic', () => {
  const mockOnTaskClick = vi.fn();

  beforeEach(() => {
    mockOnTaskClick.mockClear();
  });

  it('should mark the FIRST pending task as currently executing, not the last', () => {
    render(
      <Timeline
        trace={mockTraceWithPendingTasks}
        onTaskClick={mockOnTaskClick}
        isLoading={false}
      />
    );

    // The FIRST pending task should have "currently executing" status
    const currentlyExecutingBadges = screen.getAllByText('currently executing');
    expect(currentlyExecutingBadges).toHaveLength(1);

    // Other pending tasks should have "not started" status  
    const notStartedBadges = screen.getAllByText('not started');
    expect(notStartedBadges).toHaveLength(2);

    // Verify the correct task is marked as currently executing
    expect(screen.getByText(/First pending task - should be currently executing/)).toBeInTheDocument();
  });

  it('should show the first pending task with orange styling', () => {
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
});
