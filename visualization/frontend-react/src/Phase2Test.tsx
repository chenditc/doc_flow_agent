/**
 * Simple test component to verify Phase 2 infrastructure
 */

import React from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AppContextProvider, TraceContextProvider } from './context';
import { useTraces, useUserPreferences } from './hooks';
import { formatTime, calculateDuration, API_ENDPOINTS } from './utils';

// Create query client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30000,
      retry: 3,
    },
  },
});

// Test component to verify hooks and utilities work
const TestComponent: React.FC = () => {
  const { data: traces, isLoading, error } = useTraces();
  const { preferences, updatePreference } = useUserPreferences();

  React.useEffect(() => {
    console.log('API Endpoints:', API_ENDPOINTS);
    console.log('Format time test:', formatTime(new Date().toISOString()));
    console.log('Duration test:', calculateDuration('2025-01-01T10:00:00Z', '2025-01-01T10:05:30Z'));
  }, []);

  return (
    <div className="p-4">
      <h1 className="text-2xl font-bold mb-4">Phase 2 Infrastructure Test</h1>
      
      <div className="mb-4">
        <h2 className="text-lg font-semibold">User Preferences:</h2>
        <p>Theme: {preferences.theme}</p>
        <p>Auto Refresh: {preferences.autoRefresh ? 'Yes' : 'No'}</p>
        <button
          onClick={() => updatePreference('theme', preferences.theme === 'light' ? 'dark' : 'light')}
          className="bg-blue-500 text-white px-4 py-2 rounded mt-2"
        >
          Toggle Theme
        </button>
      </div>

      <div className="mb-4">
        <h2 className="text-lg font-semibold">Traces API:</h2>
        {isLoading && <p>Loading traces...</p>}
        {error && <p className="text-red-500">Error: {error.message}</p>}
        {traces && (
          <div>
            <p>Found {traces.length} traces</p>
            <ul className="list-disc list-inside">
              {traces.slice(0, 5).map((trace, index) => (
                <li key={index}>{trace}</li>
              ))}
            </ul>
          </div>
        )}
      </div>

      <div className="mb-4">
        <h2 className="text-lg font-semibold">Utils Test:</h2>
        <p>Current time: {formatTime(new Date().toISOString())}</p>
        <p>Duration test: {calculateDuration('2025-01-01T10:00:00Z', '2025-01-01T10:05:30Z')}</p>
      </div>
    </div>
  );
};

// Main test app with providers
const Phase2Test: React.FC = () => {
  return (
    <QueryClientProvider client={queryClient}>
      <AppContextProvider>
        <TraceContextProvider>
          <TestComponent />
        </TraceContextProvider>
      </AppContextProvider>
    </QueryClientProvider>
  );
};

export default Phase2Test;
