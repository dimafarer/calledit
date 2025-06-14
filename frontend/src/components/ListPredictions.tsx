import React, { useState, useEffect } from 'react';
import { NovaResponse, APIResponse } from '../types';
import { useAuth } from '../contexts/AuthContext';
import axios from 'axios';

/**
 * ListPredictions Component
 * 
 * This component displays a list of the user's previously saved predictions.
 * It requires authentication and fetches prediction data from the backend API.
 */

interface ListPredictionsProps {
  onNavigateToMake: () => void;
}

const ListPredictions: React.FC<ListPredictionsProps> = () => {
  const [predictions, setPredictions] = useState<NovaResponse[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { isAuthenticated, getToken } = useAuth();

  // Load predictions when component mounts or when navigated to
  useEffect(() => {
    const fetchPredictions = async () => {
      if (!isAuthenticated) {
        console.log('User not authenticated, skipping API call');
        setError('You must be logged in to view calls');
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
        
        if (err.response) {
          if (err.response.status === 401) {
            setError('Authentication failed. Please log in again.');
          } else if (err.response.status === 403) {
            setError('You do not have permission to view these predictions.');
          } else {
            setError(`Server error (${err.response.status}): ${err.response.data?.error || 'Unknown error'}`);
          }
        } else if (err.request) {
          setError('Unable to connect to the server. This might be due to network issues.');
        } else {
          setError('Failed to load calls. Please try again later.');
        }
      } finally {
        setIsLoading(false);
      }
    };

    // Always fetch when component mounts to ensure fresh data
    fetchPredictions();
  }, [isAuthenticated]);

  // Function to format date to local time
  const formatToLocalTime = (dateStr: string | undefined) => {
    if (!dateStr) return "Not available";
    try {
      const date = new Date(dateStr);
      return date.toLocaleString();
    } catch (e) {
      return dateStr;
    }
  };

  // Function to render a single prediction card
  const renderPredictionCard = (prediction: NovaResponse, index: number) => {
    const predictionDate = prediction.prediction_date || prediction.creation_date;
    
    return (
      <div key={index} className="prediction-card">
        <h3>{prediction.prediction_statement}</h3>
        <div className="prediction-details">
          {predictionDate && (
            <p><strong>Call Date:</strong> {formatToLocalTime(predictionDate)}</p>
          )}
          <p><strong>Verification Date:</strong> {formatToLocalTime(prediction.verification_date)}</p>
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
      <h2>My Calls</h2>
      
      {/* Display loading state */}
      {isLoading && (
        <div className="loading" role="status" aria-live="polite">
          Loading your calls...
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
              <p>You haven't made any calls yet.</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default ListPredictions;