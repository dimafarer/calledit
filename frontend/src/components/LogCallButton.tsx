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
    } else {
      // Handle case when there's no valid response data
      setError('No prediction data available to log. Please make a prediction first.');
    }
  };

  // Check if there's valid response data to determine if the button should be disabled
  const isDisabled = isLoading || !(response && response.results && response.results.length > 0);

  return (
    <div className="log-button-container">
      <button 
        onClick={handleLogCall}
        disabled={isDisabled}
        className="send-button"
        aria-label="Log call data"
        aria-busy={isLoading}
        title={isDisabled && !isLoading ? "Make a prediction first" : ""}
      >
        {isLoading ? 'Logging...' : 'Log Call'}
      </button>
    </div>
  );
};

export default LogCallButton;

