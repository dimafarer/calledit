import React from 'react';
import axios from 'axios';
import { APIResponse } from '../types';
import { useAuth } from '../contexts/AuthContext';

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
  // Get authentication state from AuthContext
  const { isAuthenticated, getToken } = useAuth();

  if (!isVisible) {
    return null;
  }

  const handleLogCall = async () => {
    if (response && response.results && response.results.length > 0) {
      if (!isAuthenticated) {
        setError('You must be logged in to log a prediction.');
        return;
      }

      try {
        setIsLoading(true);
        setError(null);
        const novaResponse = response.results[0];
        console.log('Sending to database:', novaResponse);
        
        // Get authentication token
        const token = getToken();
        
        // Make POST request to API Gateway endpoint
        const apiEndpoint = import.meta.env.VITE_APIGATEWAY+'/log-call';
        const result = await axios.post(apiEndpoint, {
          prediction: novaResponse
        }, {
          headers: {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'Authorization': token ? `Bearer ${token}` : ''
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

  // Check if there's valid response data and user is authenticated to determine if the button should be enabled
  const hasPrediction = response && response.results && response.results.length > 0;
  const isDisabled = isLoading || !hasPrediction || !isAuthenticated;

  // Determine the appropriate tooltip message based on what's missing
  let tooltipMessage = "";
  if (isDisabled && !isLoading) {
    if (!hasPrediction && !isAuthenticated) {
      tooltipMessage = "Make a prediction and log in first";
    } else if (!hasPrediction) {
      tooltipMessage = "Make a prediction first";
    } else if (!isAuthenticated) {
      tooltipMessage = "Log in first";
    }
  }

  return (
    <div className="log-button-container">
      <button 
        onClick={handleLogCall}
        disabled={isDisabled}
        className="send-button"
        aria-label="Log call data"
        aria-busy={isLoading}
        title={tooltipMessage}
      >
        {isLoading ? 'Logging...' : 'Log Call'}
      </button>
    </div>
  );
};

export default LogCallButton;

