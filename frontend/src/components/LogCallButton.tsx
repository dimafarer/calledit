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
 * - Navigates to the list view after successful submission
 */

interface LogCallButtonProps {
  response: APIResponse | null;
  isLoading: boolean;
  isVisible: boolean;
  setIsLoading: React.Dispatch<React.SetStateAction<boolean>>;
  setError: React.Dispatch<React.SetStateAction<string | null>>;
  setResponse: React.Dispatch<React.SetStateAction<APIResponse | null>>;
  setPrompt: React.Dispatch<React.SetStateAction<string>>;
  onSuccessfulLog?: () => void; // New callback prop for navigation
}

const LogCallButton: React.FC<LogCallButtonProps> = ({ 
  response, 
  isLoading, 
  isVisible,
  setIsLoading,
  setError,
  setResponse,
  setPrompt,
  onSuccessfulLog
}) => {
  // Get authentication state from AuthContext
  const { isAuthenticated, getToken } = useAuth();

  if (!isVisible) {
    return null;
  }

  /**
   * Handles the submission of prediction data to the database
   */
  const handleLogCall = async () => {
    if (response && response.results && response.results.length > 0) {
      if (!isAuthenticated) {
        setError('You must be logged in to log a call.');
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
        
        // Navigate to list view if callback provided, otherwise show alert
        if (onSuccessfulLog) {
          onSuccessfulLog();
        } else {
          alert('Call logged successfully!');
        }
      } catch (error) {
        console.error('Error logging call:', error);
        setError('Error occurred while logging your call');
      } finally {
        setIsLoading(false);
      }
    } else {
      // Handle case when there's no valid response data
      setError('No call data available to log. Please make a call first.');
    }
  };

  // Check if there's valid response data and user is authenticated to determine if the button should be enabled
  const hasPrediction = response && response.results && response.results.length > 0;
  const isDisabled = isLoading || !hasPrediction || !isAuthenticated;

  // Determine the appropriate tooltip message based on what's missing
  let tooltipMessage = "";
  if (isDisabled && !isLoading) {
    if (!hasPrediction && !isAuthenticated) {
      tooltipMessage = "Make a call and log in first";
    } else if (!hasPrediction) {
      tooltipMessage = "Make a call first";
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