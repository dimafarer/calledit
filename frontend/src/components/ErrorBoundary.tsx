import React from 'react';

/**
 * ErrorBoundary Component
 * 
 * This component catches JavaScript errors anywhere in its child component tree,
 * logs those errors, and displays a fallback UI instead of crashing the whole app.
 * 
 * Key features:
 * - Prevents the entire application from crashing when a component fails
 * - Logs detailed error information to the console for debugging
 * - Displays a user-friendly error message
 * - Isolates errors to specific component trees
 * 
 * Usage:
 * Wrap any component that might throw errors during rendering with this boundary:
 * <ErrorBoundary>
 *   <ComponentThatMightError />
 * </ErrorBoundary>
 */
class ErrorBoundary extends React.Component<{ children: React.ReactNode }, { hasError: boolean }> {
  constructor(props: { children: React.ReactNode }) {
    super(props);
    this.state = { hasError: false };
  }

  /**
   * Static lifecycle method called when an error is thrown in a child component
   * Returns the state update to trigger a re-render with the fallback UI
   */
  static getDerivedStateFromError(_: Error) {
    return { hasError: true };
  }

  /**
   * Lifecycle method called after an error is caught
   * Used for logging error details for debugging purposes
   */
  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error('Error caught by boundary:', error, errorInfo);
  }

  render() {
    // Display error UI if error occurred, otherwise render children
    if (this.state.hasError) {
      return (
        <div className="error-boundary">
          <h3>Something went wrong displaying the response.</h3>
          <p>Please try again.</p>
        </div>
      );
    }
    return this.props.children;
  }
}

export default ErrorBoundary;