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
    if (!prompt.trim()) return;
    
    setIsLoading(true);
    setError(null);
    
    try {
      const apiEndpoint = `${import.meta.env.VITE_APIGATEWAY}/make-call`;
      const { data } = await axios.get<APIResponse>(apiEndpoint, {
        params: { prompt },
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
