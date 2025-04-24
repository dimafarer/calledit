import React from 'react';

// Error Boundary Component - Catches and handles React rendering errors gracefully
class ErrorBoundary extends React.Component<{ children: React.ReactNode }, { hasError: boolean }> {
  constructor(props: { children: React.ReactNode }) {
    super(props);
    this.state = { hasError: false };
  }

  // Static method called when error occurs during rendering
  static getDerivedStateFromError(_: Error) {
    return { hasError: true };
  }

  // Lifecycle method to log error details
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