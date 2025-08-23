import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '../../test/test-utils'
import { TraceSelector } from '../../components/TraceSelector/TraceSelector'

// Mock the hooks and services
vi.mock('../../hooks/useRealtime', () => ({
  useRealtime: vi.fn(() => ({
    isEnabled: false,
    isConnected: false,
    startMonitoring: vi.fn(),
    stopMonitoring: vi.fn(),
  })),
}))

vi.mock('../../services/traceService', () => ({
  traceService: {
    getTraces: vi.fn(() => Promise.resolve(['trace1', 'trace2', 'trace3'])),
  },
}))

const mockProps = {
  selectedTraceId: null,
  onTraceSelected: vi.fn(),
  isLoading: false,
}

describe('TraceSelector', () => {
  it('renders without crashing', () => {
    render(<TraceSelector {...mockProps} />)
    
    expect(screen.getByText('Loading traces...')).toBeInTheDocument()
  })

  it('shows loading state correctly', () => {
    render(<TraceSelector {...mockProps} isLoading={true} />)
    
    expect(screen.getByText('Loading traces...')).toBeInTheDocument()
  })
})
