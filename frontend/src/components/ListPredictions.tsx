import React, { useState, useEffect } from 'react';
import { CallResponse, APIResponse } from '../types';
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

// Helper function to display verifiability categories with icons and colors
const getVerifiabilityDisplay = (category: string) => {
  const categoryMap: Record<string, { icon: string; label: string; color: string; bgColor: string }> = {
    'agent_verifiable': {
      icon: '🧠',
      label: 'Agent Verifiable',
      color: '#155724',
      bgColor: '#d4edda'
    },
    'current_tool_verifiable': {
      icon: '⏰',
      label: 'Time-Tool Verifiable',
      color: '#004085',
      bgColor: '#cce7ff'
    },
    'strands_tool_verifiable': {
      icon: '🔧',
      label: 'Strands-Tool Verifiable',
      color: '#721c24',
      bgColor: '#f8d7da'
    },
    'api_tool_verifiable': {
      icon: '🌐',
      label: 'API Verifiable',
      color: '#856404',
      bgColor: '#fff3cd'
    },
    'human_verifiable_only': {
      icon: '👤',
      label: 'Human Verifiable Only',
      color: '#6f42c1',
      bgColor: '#e2d9f3'
    }
  };
  
  const config = categoryMap[category] || categoryMap['human_verifiable_only'];
  
  return (
    <span style={{
      display: 'inline-flex',
      alignItems: 'center',
      gap: '6px',
      padding: '4px 12px',
      borderRadius: '16px',
      fontSize: '14px',
      fontWeight: '500',
      color: config.color,
      backgroundColor: config.bgColor,
      border: `1px solid ${config.color}20`
    }}>
      <span>{config.icon}</span>
      <span>{config.label}</span>
    </span>
  );
};

const ListPredictions: React.FC<ListPredictionsProps> = () => {
  const [predictions, setPredictions] = useState<CallResponse[]>([]);
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

  // Function to render a single call card
  const renderCallCard = (call: CallResponse, index: number) => {
    const callDate = call.prediction_date || call.creation_date;
    
    return (
      <div key={index} className="call-card">
        <h3>{call.prediction_statement}</h3>
        <div className="call-details">
          {callDate && (
            <p><strong>Call Date:</strong> {formatToLocalTime(callDate)}</p>
          )}
          <p><strong>Verification Date:</strong> {formatToLocalTime(call.verification_date)}</p>
          {call.verifiable_category && (
            <p><strong>Verifiability:</strong> {getVerifiabilityDisplay(call.verifiable_category)}</p>
          )}
          <p><strong>Status:</strong> {call.initial_status}</p>
          <details>
            <summary>Verification Method</summary>
            <div className="verification-details">
              <h4>Sources:</h4>
              <ul>
                {call.verification_method.source.map((source, idx) => (
                  <li key={`source-${idx}`}>{source}</li>
                ))}
              </ul>
              <h4>Criteria:</h4>
              <ul>
                {call.verification_method.criteria.map((criterion, idx) => (
                  <li key={`criteria-${idx}`}>{criterion}</li>
                ))}
              </ul>
              <h4>Steps:</h4>
              <ul>
                {call.verification_method.steps.map((step, idx) => (
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
        <div className="calls-list">
          {predictions.length > 0 ? (
            predictions.map((call, index) => renderCallCard(call, index))
          ) : (
            <div className="no-calls">
              <p>You haven't made any calls yet.</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default ListPredictions;