import React from 'react';
import axios from 'axios';
import { APIResponse } from '../types';

interface PredictionInputProps {
  isLoading: boolean;
  prompt: string;
  setPrompt: React.Dispatch<React.SetStateAction<string>>;
  setResponse: React.Dispatch<React.SetStateAction<APIResponse | null>>;
  setIsLoading: React.Dispatch<React.SetStateAction<boolean>>;
  setError: React.Dispatch<React.SetStateAction<string | null>>;
}

const PredictionInput: React.FC<PredictionInputProps> = ({ 
  isLoading, 
  prompt,
  setPrompt,
  setResponse, 
  setIsLoading, 
  setError 
}) => {
  const handleSubmit = async () => {
    if (prompt.trim()) {
      try {
        setIsLoading(true); // Start loading state
        setError(null); // Clear any previous errors
        const apiEndpoint = import.meta.env.VITE_APIGATEWAY+'/make-call'; // Get API URL from env
        // Make GET request to API with prompt parameter
        const result = await axios.get<APIResponse>(apiEndpoint, {
          params: { prompt },
          headers: {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
          }
        });
        
        console.log('API Response:', result.data);
        
        // Validate response data
        if (result.data && result.data.results && result.data.results.length > 0) {
          setResponse(result.data);
        } else {
          setError('Invalid response format from server');
        }
      } catch (error) {
        console.error('Error:', error);
        setError('Error occurred while processing your request');
      } finally {
        setIsLoading(false); // End loading state
      }
    }
  };

  return (
    <>
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
      <div className="button-container">
        <button 
          onClick={handleSubmit}
          disabled={isLoading || !prompt.trim()}
          className="send-button"
          aria-busy={isLoading}
        >
          {isLoading ? 'Generating...' : 'Make Call'}
        </button>
      </div>
    </>
  );
};

export default PredictionInput;
