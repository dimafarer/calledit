import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import ErrorBoundary from './ErrorBoundary';

describe('ErrorBoundary Component', () => {
  // Mock console.error to avoid test output pollution
  const originalConsoleError = console.error;
  beforeEach(() => {
    console.error = vi.fn();
  });
  
  afterEach(() => {
    console.error = originalConsoleError;
  });

  it('renders children when there is no error', () => {
    render(
      <ErrorBoundary>
        <div>Test Content</div>
      </ErrorBoundary>
    );
    
    expect(screen.getByText('Test Content')).toBeInTheDocument();
  });

  it('renders error UI when there is an error', () => {
    // Create a component that will throw an error when rendered
    const ThrowError = () => {
      throw new Error('Test error');
      return null;
    };
    
    // Suppress React's error boundary warning in test
    const spy = vi.spyOn(console, 'error');
    spy.mockImplementation(() => {});
    
    render(
      <ErrorBoundary>
        <ThrowError />
      </ErrorBoundary>
    );
    
    expect(screen.getByText('Something went wrong displaying the response.')).toBeInTheDocument();
    expect(screen.getByText('Please try again.')).toBeInTheDocument();
    
    spy.mockRestore();
  });
});