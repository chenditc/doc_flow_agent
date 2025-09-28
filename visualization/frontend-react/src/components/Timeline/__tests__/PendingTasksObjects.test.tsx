import { describe, it, expect, vi } from 'vitest';
import { render } from '@testing-library/react';
import { Timeline } from '../Timeline';
import type { TraceSession } from '../../../types/trace';

// This test ensures Timeline handles object entries (PendingTask dicts) in task_stack

describe('Timeline pending tasks with object stack entries', () => {
  const onTaskClick = vi.fn();

  const traceWithObjectStack: TraceSession = {
    session_id: 's-obj',
    start_time: '2025-01-01T00:00:00Z',
    end_time: '2025-01-01T00:10:00Z',
    initial_task_description: 'Root',
    final_status: 'running',
    engine_snapshots: {
      start: { task_stack: [], context: {}, task_execution_counter: 0 },
      end: {
        task_stack: [
          { description: 'Pending A', task_id: 'aaa111', short_name: 'A' },
          { description: 'Pending B currently executing', task_id: 'bbb222', short_name: 'B' }
        ],
        context: {},
        task_execution_counter: 1
      }
    },
    task_executions: [
      {
        task_execution_id: 'exec-1',
        task_execution_counter: 1,
        task_description: 'Executed Task 1',
        start_time: '2025-01-01T00:00:00Z',
        end_time: '2025-01-01T00:05:00Z',
        status: 'completed',
        error: null,
        engine_state_before: { task_stack: [], context: {}, task_execution_counter: 0 },
        phases: {}
      }
    ]
  };

  it('renders object-based pending tasks without error and shows status badges', () => {
    const { getByText, getAllByText } = render(<Timeline trace={traceWithObjectStack} onTaskClick={onTaskClick} isLoading={false} />);

    // Executed task
    expect(getByText('Executed Task 1')).toBeInTheDocument();
    // Pending tasks (short names used as title)
    expect(getByText('A')).toBeInTheDocument();
    expect(getByText('B')).toBeInTheDocument();

    // Status badges
    const currentBadges = getAllByText('currently executing');
    expect(currentBadges.length).toBe(1);
    const notStartedBadges = getAllByText('not started');
    expect(notStartedBadges.length).toBe(1);
  });
});
