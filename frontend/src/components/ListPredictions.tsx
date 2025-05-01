import React, { useState, useEffect } from 'react';
import { NovaResponse } from '../types';

interface ListPredictionsProps {
  onNavigateToMake: () => void;
}

const ListPredictions: React.FC<ListPredictionsProps> = ({ onNavigateToMake }) => {
  const [predictions, setPredictions] = useState<NovaResponse[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Load predictions when component mounts
  useEffect(() => {
    // This is a stub implementation that will be replaced with actual DynamoDB data later
    // For now, we'll just use some mock data
    setIsLoading(true);
    
    // Simulate API call delay
    setTimeout(() => {
      const mockPredictions: NovaResponse[] = [
        {
          prediction_statement: "The price of Bitcoin will exceed $100,000 by December 2023",
          verification_date: "2023-12-31",
          verification_method: {
            source: ["CoinMarketCap", "Binance", "Coinbase"],
            criteria: ["Closing price on any major exchange exceeds $100,000"],
            steps: ["Check price on December 31, 2023", "Document screenshots from multiple exchanges"]
          },
          initial_status: "Pending"
        },
        {
          prediction_statement: "SpaceX will successfully land humans on Mars by 2026",
          verification_date: "2026-12-31",
          verification_method: {
            source: ["NASA", "SpaceX official announcements", "International news coverage"],
            criteria: ["Confirmed human landing on Mars surface", "Live video transmission from Mars"],
            steps: ["Monitor SpaceX launches", "Verify through multiple news sources", "Check official space agency confirmations"]
          },
          initial_status: "Pending"
        },
        {
          prediction_statement: "Artificial General Intelligence will be achieved by 2030",
          verification_date: "2030-12-31",
          verification_method: {
            source: ["Academic publications", "Tech company announcements", "AI benchmark tests"],
            criteria: ["System passes comprehensive Turing test", "Demonstrates general problem solving across domains"],
            steps: ["Monitor AI research breakthroughs", "Evaluate against established AGI criteria", "Verify independent testing results"]
          },
          initial_status: "Pending"
        }
      ];
      
      setPredictions(mockPredictions);
      setIsLoading(false);
    }, 1000);
  }, []);

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
      
      {/* Button to navigate back to MakePredictions */}
      <div className="navigation-button-container">
        <button 
          onClick={onNavigateToMake}
          className="navigation-button"
          aria-label="Make a new prediction"
        >
          Make New Prediction
        </button>
      </div>
      
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