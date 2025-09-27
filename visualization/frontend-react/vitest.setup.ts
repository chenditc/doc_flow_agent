// Polyfills and global test setup
import { expect, afterEach } from 'vitest';
import '@testing-library/jest-dom/vitest';
import { cleanup } from '@testing-library/react';

// Ensure DOM is cleaned between tests to avoid duplicate elements
afterEach(() => {
  cleanup();
});

if (typeof window !== 'undefined' && !window.matchMedia) {
  // Basic matchMedia polyfill sufficient for @textea/json-viewer dark mode detection
  window.matchMedia = (query: string): MediaQueryList => {
    return {
      matches: false,
      media: query,
      onchange: null,
      addEventListener: () => {},
      removeEventListener: () => {},
      addListener: () => {}, // deprecated
      removeListener: () => {}, // deprecated
      dispatchEvent: () => false
    } as any;
  };
}
