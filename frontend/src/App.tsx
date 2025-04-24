// Import necessary dependencies from React and other libraries
import { useState } from 'react' // useState hook for managing component state
import React from 'react' // Core React library
import axios from 'axios' // HTTP client for making API requests
import './App.css' // Component styles

// TypeScript interfaces define the shape of our API response data
interface VerificationMethod {
  source: string[]; // Array of verification sources
  criteria: string[]; // Array of verification criteria  
  steps: string[]; // Array of verification steps
}

interface NovaResponse {
  prediction_statement: string; // The prediction text
  verification_date: string; // When prediction will be verified
  verification_method: VerificationMethod; // Nested verification details
  initial_status: string; // Initial prediction status
}

interface APIResponse {
  results: NovaResponse[]; // Array of prediction responses
}

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

// Main App Component
function App() {
  // State management using React hooks
  const [prompt, setPrompt] = useState('') // Store user input
  const [response, setResponse] = useState<APIResponse | null>(null) // Store API response
  const [isLoading, setIsLoading] = useState(false) // Track loading state
  const [error, setError] = useState<string | null>(null) // Store error messages

  // Handler for form submission
  const handleSubmit = async () => {
    try {
      setIsLoading(true) // Start loading state
      setError(null) // Clear any previous errors
      const apiEndpoint = import.meta.env.VITE_APIGATEWAY // Get API URL from env
      // Make GET request to API with prompt parameter
      const result = await axios.get<APIResponse>(apiEndpoint, {
        params: { prompt: prompt },
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json'
        }
      })
      
      console.log('API Response:', result.data)
      
      // Validate response data
      if (result.data && result.data.results && result.data.results.length > 0) {
        setResponse(result.data)
      } else {
        setError('Invalid response format from server')
      }
    } catch (error) {
      console.error('Error:', error)
      setError('Error occurred while processing your request')
    } finally {
      setIsLoading(false) // End loading state
    }
  }

  // Helper function to render verification method details
  const renderVerificationMethod = (method: VerificationMethod) => {
    // Validate required data exists
    if (!method || !method.source || !method.criteria || !method.steps) {
      return <div className="error-message">Verification method data is incomplete</div>;
    }
    
    // Render verification details in structured format
    return (
      <div className="verification-method">
        <div className="method-section">
          <h3>Sources:</h3>
          <ul>
            {Array.isArray(method.source) ? (
              method.source.map((src, index) => (
                <li key={`source-${index}`}>{String(src)}</li>
              ))
            ) : (
              <li>No sources available</li>
            )}
          </ul>
        </div>
        <div className="method-section">
          <h3>Criteria:</h3>
          <ul>
            {Array.isArray(method.criteria) ? (
              method.criteria.map((criterion, index) => (
                <li key={`criteria-${index}`}>{String(criterion)}</li>
              ))
            ) : (
              <li>No criteria available</li>
            )}
          </ul>
        </div>
        <div className="method-section">
          <h3>Steps:</h3>
          <ul>
            {Array.isArray(method.steps) ? (
              method.steps.map((step, index) => (
                <li key={`step-${index}`}>{String(step)}</li>
              ))
            ) : (
              <li>No steps available</li>
            )}
          </ul>
        </div>
      </div>
    );
  };

  // Helper function to render API response or appropriate message
  const renderResponse = () => {
    if (error) {
      return <div className="error-message">{error}</div>;
    }

    if (!response || !response.results || !response.results[0]) {
      return <div className="placeholder">Enter a prediction above and click Send</div>;
    }

    const novaResponse = response.results[0];

    // Render structured response data
    return (
      <div className="structured-response">
        <div className="response-field">
          <h3>Prediction Statement:</h3>
          <p>{novaResponse.prediction_statement}</p>
        </div>
        <div className="response-field">
          <h3>Verification Date:</h3>
          <p>{novaResponse.verification_date}</p>
        </div>
        <div className="response-field">
          <h3>Verification Method:</h3>
          {novaResponse.verification_method && (
            <ErrorBoundary>
              {renderVerificationMethod(novaResponse.verification_method)}
            </ErrorBoundary>
          )}
        </div>
        <div className="response-field">
          <h3>Initial Status:</h3>
          <p>{novaResponse.initial_status}</p>
        </div>
      </div>
    );
  };

  // Component's main render method
  return (
    <div className="app-container">
      <h1>Call It!!</h1>
      {/* Input section */}
      <div className="input-container">
        <textarea
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder="Enter your prediction here..."
          rows={4}
          className="text-box"
          aria-label="Prediction input"
        />
      </div>
      {/* Submit button section */}
      <div className="button-container">
        <button 
          onClick={handleSubmit}
          disabled={isLoading || !prompt.trim()}
          className="send-button"
          aria-busy={isLoading}
        >
          {isLoading ? 'Sending...' : 'Send'}
        </button>
      </div>
      {/* Response display section */}
      <div className="response-container">
        <ErrorBoundary>
          {isLoading ? (
            <div className="loading" role="status" aria-live="polite">
              Processing your request...
            </div>
          ) : (
            renderResponse()
          )}
        </ErrorBoundary>
      </div>
    </div>
  )
}

export default App
