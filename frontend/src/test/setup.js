import '@testing-library/jest-dom';
import { vi } from 'vitest';

// jsdom may omit matchMedia; some environments parse max-width against a tiny viewport
// and return matches: true, which hides the desktop navbar. Default to "wide" for tests.
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  configurable: true,
  value: vi.fn().mockImplementation((query) => ({
    matches: false,
    media: query,
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
});
