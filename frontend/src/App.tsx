// Import necessary dependencies from React and other libraries
import { useState, useEffect } from 'react' // useState and useEffect hooks for managing component state
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
// import { TestAuth } from './components/TestAuth';

// Import storage utilities
import { getPredictionData, savePredictionData } from './utils/storageUtils';

// Main App Component
function App() {
  // State management using React hooks
  // Initialize response state from local storage if available
  const [response, setResponse] = useState<APIResponse | null>(() => getPredictionData()) 
  const [isLoading, setIsLoading] = useState(false) // Track loading state
  const [error, setError] = useState<string | null>(null) // Store error messages
  const [prompt, setPrompt] = useState('') // Store the prediction input text

  // Save prediction data to local storage whenever it changes
  useEffect(() => {
    savePredictionData(response);
  }, [response]);

  // Custom response setter that updates state and saves to local storage
  const handleSetResponse: React.Dispatch<React.SetStateAction<APIResponse | null>> = (newResponse) => {
    setResponse(newResponse);
    // Note: We don't need to explicitly call savePredictionData here
    // as the useEffect above will handle that
  };

  // Component's main render method
  return (
    <AuthProvider>
      <div className="app-container">
        {/* <div>
          <h1>Your App</h1>
          <TestAuth />
        </div> */}
        <h1>Call It!!</h1>
        
        {/* Prediction Input Component */}
        <PredictionInput 
          isLoading={isLoading}
          prompt={prompt}
          setPrompt={setPrompt}
          setResponse={handleSetResponse}
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
              setResponse={handleSetResponse}
              setPrompt={setPrompt}
            />
            <LoginButton />
          </div>
        </div>
      </div>
    </AuthProvider>
  )
}

export default App







