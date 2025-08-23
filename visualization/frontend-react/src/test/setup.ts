import '@testing-library/jest-dom';
import { afterEach } from 'vitest';
import { cleanup } from '@testing-library/react';

// Ensure we clean up DOM after each test to avoid cross-test contamination
afterEach(() => {
  cleanup();
});
