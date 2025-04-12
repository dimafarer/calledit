import { useState } from 'react'
import axios from 'axios'
import './App.css'

function App() {
  const [prompt, setPrompt] = useState('')
  const [response, setResponse] = useState('')
  const [isLoading, setIsLoading] = useState(false)

  const handleSubmit = async () => {
    try {
      setIsLoading(true)
      const apiEndpoint = import.meta.env.VITE_APIGATEWAY
      const result = await axios.get(apiEndpoint, {
        // params: { prompt },
        params: { prompt: prompt }, // Explicitly naming the parameter 'prompt'
        headers: {
          'Content-Type': 'application/json',
        },
        withCredentials: false // Add this if you're not using credentials
      })
      setResponse(result.data)
    } catch (error) {
      console.error('Error:', error)
      setResponse('Error occurred while processing your request')
    } finally {
      setIsLoading(false)
    }
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
        <textarea
          value={response.message}
          readOnly
          placeholder="Response will appear here..."
          rows={4}
          className="text-box"
        />
      </div>
    </div>
  )
}

export default App

