import { useState } from 'react'
import axios from 'axios'
import './App.css'


// Define interfaces for the response structure
interface VerificationMethod {
  source: string | string[];
  criteria: string | string[];
  steps: string | string[];
}

interface NovaResponse {
  prediction_statement: string;
  verification_date: string;
  verification_method: VerificationMethod;
  initial_status: string;
}

interface APIResponse {
  results: NovaResponse[];
}


function App() {
  const [prompt, setPrompt] = useState('')
  const [response, setResponse] = useState<NovaResponse | string | null>(null)
  const [isLoading, setIsLoading] = useState(false)

  const handleSubmit = async () => {
    try {
      setIsLoading(true)
      const apiEndpoint = import.meta.env.VITE_APIGATEWAY
      const result = await axios.get(apiEndpoint, {
        params: { prompt: prompt },
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json'
        }
      })
      console.log('API Response:', result.data)
      
      // Extract the first result from the API response
      const apiResponse = result.data as APIResponse
      if (apiResponse.results && apiResponse.results.length > 0) {
        setResponse(apiResponse.results[0])
      } else {
        setResponse('No results found in the response')
      }
    } catch (error) {
      console.error('Error:', error)
      setResponse('Error occurred while processing your request')
    } finally {
      setIsLoading(false)
    }
  }

  const renderVerificationMethod = (method: VerificationMethod | undefined) => {
    if (!method) {
      return <div className="error-message">Verification method not available</div>;
    }
    
    return (
      <div className="verification-method">
        <div className="method-section">
          <h3>Sources:</h3>
          <ul>
            {Array.isArray(method.source) ? (
              method.source.map((src, index) => (
                <li key={`source-${index}`}>{src}</li>
              ))
            ) : (
              <li>{method.source}</li>
            )}
          </ul>
        </div>
        <div className="method-section">
          <h3>Criteria:</h3>
          <ul>
            {Array.isArray(method.criteria) ? (
              method.criteria.map((criterion, index) => (
                <li key={`criteria-${index}`}>{criterion}</li>
              ))
            ) : (
              <li>{method.criteria}</li>
            )}
          </ul>
        </div>
        <div className="method-section">
          <h3>Steps:</h3>
          <ul>
            {Array.isArray(method.steps) ? (
              method.steps.map((step, index) => (
                <li key={`step-${index}`}>{step}</li>
              ))
            ) : (
              <li>{method.steps}</li>
            )}
          </ul>
        </div>
      </div>
    );
  };

  const renderResponse = () => {
    if (typeof response === 'string') {
      return <div className="error-message">{response}</div>
    }

    if (!response) {
      return <div className="placeholder">Response will appear here...</div>
    }

    return (
      <div className="structured-response">
        <div className="response-field">
          <h3>Prediction Statement:</h3>
          <p>{response.prediction_statement}</p>
        </div>
        <div className="response-field">
          <h3>Verification Date:</h3>
          <p>{response.verification_date}</p>
        </div>
        <div className="response-field">
          <h3>Verification Method:</h3>
          {renderVerificationMethod(response.verification_method)}
        </div>
        <div className="response-field">
          <h3>Initial Status:</h3>
          <p>{response.initial_status}</p>
        </div>
      </div>
    )
  }

  return (
    <div className="app-container">
      <h1>Prompt Response System</h1>
      <div className="input-container">
        <textarea
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder="Enter your prompt here..."
          rows={4}
          className="text-box"
        />
      </div>
      <div className="button-container">
        <button 
          onClick={handleSubmit}
          disabled={isLoading || !prompt.trim()}
          className="send-button"
        >
          {isLoading ? 'Sending...' : 'Send'}
        </button>
      </div>
      <div className="response-container">
        {isLoading ? (
          <div className="loading">Processing your request...</div>
        ) : (
          renderResponse()
        )}
      </div>
    </div>
  )
}

export default App








