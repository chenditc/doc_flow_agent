import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { TraceContextProvider } from './context/TraceContext';
import { Timeline } from './components/Timeline/Timeline';
import { TraceSelector } from './components/TraceSelector/TraceSelector';

// Create a client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <TraceContextProvider>
        <div className="min-h-screen bg-gray-50">
          <header className="bg-white shadow-sm border-b border-gray-200">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
              <div className="py-4">
                <h1 className="text-2xl font-bold text-gray-900">Doc Flow Trace Viewer</h1>
                <p className="text-sm text-gray-600 mt-1">Real-time visualization of task execution traces</p>
              </div>
            </div>
          </header>
          
          <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
            <div className="mb-6">
              <TraceSelector selectedTraceId={null} onTraceSelected={() => {}} />
            </div>
            <Timeline trace={null} onTaskClick={() => {}} />
          </main>
        </div>
      </TraceContextProvider>
    </QueryClientProvider>
  );
}

export default App;
