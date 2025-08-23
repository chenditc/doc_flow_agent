import type { ReactElement } from 'react';
import { render as rtlRender } from '@testing-library/react';
import type { RenderOptions } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { TraceContextProvider } from '../context/TraceContext';

const createQueryClient = () => new QueryClient({
  defaultOptions: { queries: { retry: false } }
});

function AllProviders({ children }: { children?: React.ReactNode }) {
  const client = createQueryClient();
  return (
    <QueryClientProvider client={client}>
      <TraceContextProvider>{children}</TraceContextProvider>
    </QueryClientProvider>
  );
}

export function render(ui: ReactElement, options?: Omit<RenderOptions, 'queries'>) {
  return rtlRender(ui, { wrapper: AllProviders, ...options });
}

// Re-export everything from testing-library so consumers can use its utilities
export * from '@testing-library/react';

// Also export our custom render as default named export to keep compatibility
export { render as customRender };
