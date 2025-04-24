import React from 'react';
import axios from 'axios';
import { APIResponse } from '../types';

interface LogCallButtonProps {
  response: APIResponse | null;
  isLoading: boolean;
  isVisible: boolean;
  setIsLoading: React.Dispatch<React.SetStateAction<boolean>>;
  setError: React.Dispatch<React.SetStateAction<string | null>>;
}

const LogCallButton: React.FC<LogCallButtonProps> = ({ 
  response, 
  isLoading, 
  isVisible,
  setIsLoading,
  setError
}) => {
  if (!isVisible) {
    return null;
  }

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
  };

  return (
    <div className="log-button-container">
      <button 
        onClick={handleLogCall}
        disabled={isLoading}
        className="send-button"
        aria-label="Log call data"
        aria-busy={isLoading}
      >
        {isLoading ? 'Logging...' : 'Log Call'}
      </button>
    </div>
  );
};

export default LogCallButton;
