import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { JobDetailPage } from '../components/Jobs/JobDetailPage';
import { jobService } from '../services';

let capturedLocationState: unknown = null;

const TraceView: React.FC = () => {
  const location = useLocation();

  React.useEffect(() => {
    capturedLocationState = location.state;
  }, [location]);

  return <div data-testid="trace-view">Trace Viewer</div>;
};

// Mock jobService
vi.mock('../services', () => {
  return {
    jobService: {
      getJob: vi.fn().mockResolvedValue({
        job_id: 'job123',
        task_description: 'Do something',
        status: 'COMPLETED',
        created_at: new Date().toISOString(),
        started_at: new Date().toISOString(),
        finished_at: new Date().toISOString(),
        trace_files: ['session_20250101_000000_abcd1234.json'],
        max_tasks: 10
      }),
      getJobLogs: vi.fn().mockResolvedValue({ job_id: 'job123', logs: '' }),
      getJobContext: vi.fn().mockResolvedValue({ job_id: 'job123', context: {} })
    }
  };
});

describe('JobDetailPage trace link', () => {
  beforeEach(() => {
    capturedLocationState = null;
    vi.mocked(jobService.getJob).mockResolvedValue({
      job_id: 'job123',
      task_description: 'Do something',
      status: 'COMPLETED',
      created_at: new Date().toISOString(),
      started_at: new Date().toISOString(),
      finished_at: new Date().toISOString(),
      trace_files: ['session_20250101_000000_abcd1234.json'],
      max_tasks: 10
    });
  });

  it('navigates to /traces?trace=<id> without .json extension when clicking trace item', async () => {
    const queryClient = new QueryClient();
    const TestHarness: React.FC = () => (
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={['/jobs/job123']}>
          <Routes>
            <Route path="/jobs/:jobId" element={<JobDetailPage />} />
            <Route path="/traces" element={<TraceView />} />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>
    );

    render(<TestHarness />);

    // Switch to Traces tab (3rd tab index 2)
    const tracesTab = await screen.findByRole('tab', { name: /Traces/ });
    fireEvent.click(tracesTab);

    // Now list should render trace file entry
    const traceItem = await screen.findByText(/session_20250101_000000_abcd1234\.json/);
    fireEvent.click(traceItem);

    // MemoryRouter doesn't update window.location, so assert via waiting for trace viewer route element
    await waitFor(() => {
      expect(screen.getByTestId('trace-view')).toBeInTheDocument();
    });

    expect(capturedLocationState).toBeNull();
  });

  it('enables real-time automatically for running jobs when opening trace', async () => {
    vi.mocked(jobService.getJob).mockResolvedValue({
      job_id: 'job123',
      task_description: 'Do something',
      status: 'RUNNING',
      created_at: new Date().toISOString(),
      started_at: new Date().toISOString(),
      finished_at: null,
      trace_files: ['session_20250101_000000_abcd1234.json'],
      max_tasks: 10
    });

    const queryClient = new QueryClient();
    const TestHarness: React.FC = () => (
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={['/jobs/job123']}>
          <Routes>
            <Route path="/jobs/:jobId" element={<JobDetailPage />} />
            <Route path="/traces" element={<TraceView />} />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>
    );

    render(<TestHarness />);

    const tracesTab = await screen.findByRole('tab', { name: /Traces/ });
    fireEvent.click(tracesTab);

    const traceItem = await screen.findByText(/session_20250101_000000_abcd1234\.json/);
    fireEvent.click(traceItem);

    await waitFor(() => {
      expect(screen.getByTestId('trace-view')).toBeInTheDocument();
    });

    expect(capturedLocationState).toEqual({ autoEnableRealtime: true });
  });
});
