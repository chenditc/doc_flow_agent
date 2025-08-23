import { createRoot } from 'react-dom/client';

// Test the modules step by step
console.log('=== Starting debug test ===');

try {
  console.log('1. Testing ApiClient import...');
  const { ApiClient } = await import('./services/api');
  console.log('ApiClient imported successfully:', ApiClient);
  
  console.log('2. Testing ApiClient instantiation...');
  const apiClient = new ApiClient({ baseUrl: 'http://localhost:8000' });
  console.log('ApiClient instantiated successfully:', apiClient);
  
  console.log('3. Testing TraceService import...');
  const { TraceService } = await import('./services/traceService');
  console.log('TraceService imported successfully:', TraceService);
  
  console.log('4. Testing TraceService instantiation...');
  const traceService = new TraceService(apiClient);
  console.log('TraceService instantiated successfully:', traceService);
  
  console.log('5. Testing getTraces method...');
  const traces = await traceService.getTraces();
  console.log('getTraces called successfully:', traces);
  
} catch (error) {
  console.error('Error in debug test:', error);
  if (error instanceof Error) {
    console.error('Error stack:', error.stack);
  }
}

function DebugComponent() {
  return (
    <div>
      <h1>Debug Test</h1>
      <p>Check the browser console for debug output.</p>
    </div>
  );
}

// Mount the component
const root = document.getElementById('root');
if (root) {
  createRoot(root).render(<DebugComponent />);
}
