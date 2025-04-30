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
  LoginButton,
} from './components'

// Import auth provider
import { AuthProvider } from './contexts/AuthContext'

// Main App Component
function App() {
  // State management using React hooks
  const [response, setResponse] = useState<APIResponse | null>(null) // Store API response
  const [isLoading, setIsLoading] = useState(false) // Track loading state
  const [error, setError] = useState<string | null>(null) // Store error messages

  // Component's main render method
  return (
    <AuthProvider>
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
          <div className="buttons-container">
            <LogCallButton
              response={response}
              isLoading={isLoading}
              isVisible={true}
              setIsLoading={setIsLoading}
              setError={setError}
            />
            <LoginButton />
          </div>
        </div>
      </div>
    </AuthProvider>
  )
}

export default App










