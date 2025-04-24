// Import necessary dependencies from React and other libraries
import { useState } from 'react' // useState hook for managing component state
import axios from 'axios' // HTTP client for making API requests
import './App.css' // Component styles

// Import types
import { APIResponse } from './types'

// Import components
import { 
  PredictionInput, 
  PredictionDisplay, 
  LogCallButton,
  ErrorBoundary 
} from './components'

// Main App Component
function App() {
  // State management using React hooks
  const [response, setResponse] = useState<APIResponse | null>(null) // Store API response
  const [isLoading, setIsLoading] = useState(false) // Track loading state
  const [error, setError] = useState<string | null>(null) // Store error messages

  // Handler for form submission
  const handleSubmit = async (prompt: string) => {
    try {
      setIsLoading(true) // Start loading state
      setError(null) // Clear any previous errors
      const apiEndpoint = import.meta.env.VITE_APIGATEWAY+'/make-call' // Get API URL from env
      // Make GET request to API with prompt parameter
      const result = await axios.get<APIResponse>(apiEndpoint, {
        params: { prompt },
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
  
  // Handler for logging call data
  const handleLogCall = async () => {
    if (response && response.results && response.results.length > 0) {
      try {
        setIsLoading(true);
        setError(null);
        const novaResponse = response.results[0];
        console.log('Sending to database:', novaResponse);
        
        // Make POST request to API Gateway endpoint
        const apiEndpoint = import.meta.env.VITE_APIGATEWAY+'/log-call';
        const result = await axios.post(apiEndpoint, {
          prediction: novaResponse
        }, {
          headers: {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
          }
        });
        
        console.log('Log response:', result.data);
        alert('Prediction logged successfully!');
      } catch (error) {
        console.error('Error logging call:', error);
        setError('Error occurred while logging your prediction');
      } finally {
        setIsLoading(false);
      }
    }
  }

  // Component's main render method
  return (
    <div className="app-container">
      <h1>Call It!!</h1>
      
      {/* Prediction Input Component */}
      <PredictionInput 
        onSubmit={handleSubmit}
        isLoading={isLoading}
      />
      
      {/* Response display section */}
      <div className="response-container">
        <PredictionDisplay
          response={response}
          error={error}
          isLoading={isLoading}
        />
        
        {/* Log Call Button Component */}
        <LogCallButton
          onLogCall={handleLogCall}
          isLoading={isLoading}
          isVisible={!!(response && response.results && response.results.length > 0)}
        />
      </div>
    </div>
  )
}

export default App





