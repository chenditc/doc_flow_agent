/// <reference types="vitest" />
import { describe, it, expect } from 'vitest';
import { render, screen } from '../test/test-utils';
import App from '../App';

describe('App (integration)', () => {
  it('renders the header and main layout', () => {
    render(<App />);

    // Header text from Header component
    expect(screen.getByText(/Doc Flow Trace Viewer/i)).toBeInTheDocument();

    // Main element should be present
    expect(screen.getByRole('main')).toBeInTheDocument();
  });
});
