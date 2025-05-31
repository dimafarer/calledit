import axios from 'axios';
import { APIResponse } from '../types';

/**
 * PredictionInput Component
 * 
 * This component provides the user interface for entering prediction text
 * and submitting it to the API for processing.
 * 
 * Features:
 * - Text area for entering prediction statements
 * - Submit button with appropriate loading and disabled states
 * - Error handling for API requests
 * - Integration with the parent component's state management
 * 
 * The component makes API calls to the strands-make-call endpoint which
 * processes the user's prediction text and returns structured prediction data.
 */

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
  /**
   * Handles the submission of the prediction text to the API
   * 
   * This function:
   * 1. Validates that the prompt is not empty
   * 2. Sets loading state and clears any previous errors
   * 3. Makes an API request to the strands-make-call endpoint
   * 4. Updates the parent component with the response data
   * 5. Handles any errors that occur during the process
   */
  const handleSubmit = async () => {
    if (!prompt.trim()) return;
    
    setIsLoading(true);
    setError(null);
    
    try {
      // Get user's timezone
      const userTimezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
      
      // Using the strands-make-call endpoint for AI-powered prediction processing
      const apiEndpoint = `${import.meta.env.VITE_APIGATEWAY}/strands-make-call`;
      const { data } = await axios.get<APIResponse>(apiEndpoint, {
        params: { prompt, timezone: userTimezone },
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json'
        }
      });
      
      if (data?.results?.length > 0) {
        setResponse(data);
      } else {
        setError('Invalid response format from server');
      }
    } catch (error) {
      console.error('Error:', error);
      setError('Error occurred while processing your request');
    } finally {
      setIsLoading(false);
    }
  };

  const isDisabled = isLoading || !prompt.trim();

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
          disabled={isLoading}
        />
      </div>
      <div className="button-container">
        <button 
          onClick={handleSubmit}
          disabled={isDisabled}
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
