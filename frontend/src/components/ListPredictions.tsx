import React, { useState, useEffect } from 'react';
import { NovaResponse, APIResponse } from '../types';
import { useAuth } from '../contexts/AuthContext';
import axios from 'axios';

/**
 * ListPredictions Component
 * 
 * This component displays a list of the user's previously saved predictions.
 * It requires authentication and fetches prediction data from the backend API.
 * 
 * Key features:
 * - Fetches predictions when the component mounts if the user is authenticated
 * - Displays loading states during API calls
 * - Handles and displays various error conditions with specific messages
 * - Renders each prediction in a structured card format with expandable details
 * - Shows a message when no predictions are available
 * 
 * The component uses the AuthContext to get authentication status and tokens
 * needed for making authenticated API requests.
 */

interface ListPredictionsProps {
  onNavigateToMake: () => void;
}

const ListPredictions: React.FC<ListPredictionsProps> = ({ onNavigateToMake }) => {
  const [predictions, setPredictions] = useState<NovaResponse[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { isAuthenticated, getToken } = useAuth();

  // Load predictions when component mounts
  useEffect(() => {
    const fetchPredictions = async () => {
      if (!isAuthenticated) {
        console.log('User not authenticated, skipping API call');
        setError('You must be logged in to view predictions');
        return;
      }

      setIsLoading(true);
      setError(null);

      try {
        console.log('Fetching predictions from /list-predictions endpoint');
        const token = getToken();
        const apiEndpoint = import.meta.env.VITE_APIGATEWAY + '/list-predictions';
        
        const response = await axios.get<APIResponse>(apiEndpoint, {
          headers: {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'Authorization': token ? `Bearer ${token}` : ''
          }
        });

        console.log('Received predictions response:', response);
        setPredictions(response.data.results || []);
        console.log(`Loaded ${response.data.results?.length || 0} predictions`);
      } catch (err: any) {
        console.error('Error fetching predictions:', err);
        console.error('Error details:', err.message);
        
        // Provide more specific error messages based on the error type
        if (err.response) {
          console.error('Response status:', err.response.status);
          console.error('Response data:', err.response.data);
          
          if (err.response.status === 401) {
            setError('Authentication failed. Please log in again.');
          } else if (err.response.status === 403) {
            setError('You do not have permission to view these predictions.');
          } else {
            setError(`Server error (${err.response.status}): ${err.response.data?.error || 'Unknown error'}`);
          }
        } else if (err.request) {
          // The request was made but no response was received (CORS issue)
          setError('Unable to connect to the server. This might be due to network issues or CORS restrictions.');
          console.error('CORS or network issue detected. Request details:', err.request);
        } else {
          setError('Failed to load predictions. Please try again later.');
        }
      } finally {
        setIsLoading(false);
      }
    };

    fetchPredictions();
  }, [isAuthenticated]);

  // Function to render a single prediction card
  const renderPredictionCard = (prediction: NovaResponse, index: number) => {
    return (
      <div key={index} className="prediction-card">
        <h3>{prediction.prediction_statement}</h3>
        <div className="prediction-details">
          <p><strong>Verification Date:</strong> {prediction.verification_date}</p>
          <p><strong>Status:</strong> {prediction.initial_status}</p>
          <details>
            <summary>Verification Method</summary>
            <div className="verification-details">
              <h4>Sources:</h4>
              <ul>
                {prediction.verification_method.source.map((source, idx) => (
                  <li key={`source-${idx}`}>{source}</li>
                ))}
              </ul>
              <h4>Criteria:</h4>
              <ul>
                {prediction.verification_method.criteria.map((criterion, idx) => (
                  <li key={`criteria-${idx}`}>{criterion}</li>
                ))}
              </ul>
              <h4>Steps:</h4>
              <ul>
                {prediction.verification_method.steps.map((step, idx) => (
                  <li key={`step-${idx}`}>{step}</li>
                ))}
              </ul>
            </div>
          </details>
        </div>
      </div>
    );
  };

  return (
    <div className="list-predictions-container">
      <h2>My Predictions</h2>
      
      {/* Display loading state */}
      {isLoading && (
        <div className="loading" role="status" aria-live="polite">
          Loading your predictions...
        </div>
      )}
      
      {/* Display error if any */}
      {error && (
        <div className="error-message">
          {error}
        </div>
      )}
      
      {/* Display predictions */}
      {!isLoading && !error && (
        <div className="predictions-list">
          {predictions.length > 0 ? (
            predictions.map((prediction, index) => renderPredictionCard(prediction, index))
          ) : (
            <div className="no-predictions">
              <p>You haven't made any predictions yet.</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default ListPredictions;
