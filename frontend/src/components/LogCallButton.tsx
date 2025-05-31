import React from 'react';
import axios from 'axios';
import { APIResponse } from '../types';
import { useAuth } from '../contexts/AuthContext';
import { clearPredictionData } from '../utils/storageUtils';

/**
 * LogCallButton Component
 * 
 * This component provides functionality for users to save their predictions
 * to the database. It requires authentication and handles the API interaction
 * for storing prediction data.
 * 
 * Features:
 * - Validates that the user is authenticated before allowing submission
 * - Sends prediction data to the backend API with authentication token
 * - Provides appropriate feedback during and after the submission process
 * - Clears local prediction data after successful submission
 * - Shows appropriate tooltips based on the current state (needs login, needs prediction)
 * 
 * The button is conditionally enabled/disabled based on:
 * 1. Whether there is valid prediction data to submit
 * 2. Whether the user is authenticated
 * 3. Whether a submission is currently in progress
 */

interface LogCallButtonProps {
  response: APIResponse | null;
  isLoading: boolean;
  isVisible: boolean;
  setIsLoading: React.Dispatch<React.SetStateAction<boolean>>;
  setError: React.Dispatch<React.SetStateAction<string | null>>;
  setResponse: React.Dispatch<React.SetStateAction<APIResponse | null>>;
  setPrompt: React.Dispatch<React.SetStateAction<string>>;
}

const LogCallButton: React.FC<LogCallButtonProps> = ({ 
  response, 
  isLoading, 
  isVisible,
  setIsLoading,
  setError,
  setResponse,
  setPrompt
}) => {
  // Get authentication state from AuthContext
  const { isAuthenticated, getToken } = useAuth();

  if (!isVisible) {
    return null;
  }

  /**
   * Handles the submission of prediction data to the database
   * 
   * This function:
   * 1. Validates that there is prediction data to submit
   * 2. Checks that the user is authenticated
   * 3. Sends the prediction data to the backend API
   * 4. Handles the response and updates the UI accordingly
   * 5. Clears local data after successful submission
   */
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
        
        // Clear prediction data from local storage after successful log
        clearPredictionData();
        
        // Clear the response state to update the UI
        setResponse(null);
        
        // Clear the prompt text
        setPrompt('');
        
        // Show success message
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
