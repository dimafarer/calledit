import '@testing-library/jest-dom';
import { vi } from 'vitest';

// Mock window.alert
window.alert = vi.fn();

// Setup global test environment
beforeAll(() => {
  // Add any global setup here
});

afterAll(() => {
  // Add any global teardown here
});

// Reset mocks between tests
beforeEach(() => {
  vi.resetAllMocks();
});