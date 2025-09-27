/// <reference types="vitest" />
import { describe, it, expect } from 'vitest';
import { render } from '../test/test-utils';
import App from '../App';

describe('App (integration)', () => {
  it('renders the header and main layout', () => {
  const { getByText, getByRole } = render(<App />);
  expect(getByText(/Doc Flow Agent/i)).toBeInTheDocument();
  expect(getByRole('main')).toBeInTheDocument();
  });
});
