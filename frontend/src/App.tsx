// Import necessary dependencies from React and other libraries
import { useState } from 'react' // useState hook for managing component state
import './App.css' // Component styles

// Import types
import { APIResponse } from './types'

// Import components
import { 
  PredictionInput, 
  PredictionDisplay, 
  LogCallButton,
} from './components'

// Main App Component
function App() {
  // State management using React hooks
  const [response, setResponse] = useState<APIResponse | null>(null) // Store API response
  const [isLoading, setIsLoading] = useState(false) // Track loading state
  const [error, setError] = useState<string | null>(null) // Store error messages

  // Component's main render method
  return (
    <div className="app-container">
      <h1>Call It!!</h1>
      
      {/* Prediction Input Component */}
      <PredictionInput 
        isLoading={isLoading}
        setResponse={setResponse}
        setIsLoading={setIsLoading}
        setError={setError}
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
          response={response}
          isLoading={isLoading}
          isVisible={!!(response && response.results && response.results.length > 0)}
          setIsLoading={setIsLoading}
          setError={setError}
        />
      </div>
    </div>
  )
}

export default App






