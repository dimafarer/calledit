import React from 'react';
import { APIResponse, VerificationMethod } from '../types';
import ErrorBoundary from './ErrorBoundary';

interface PredictionDisplayProps {
  response: APIResponse | null;
  error: string | null;
  isLoading: boolean;
}

const PredictionDisplay: React.FC<PredictionDisplayProps> = ({ response, error, isLoading }) => {
  // Helper function to render verification method details
  const renderVerificationMethod = (method: VerificationMethod) => {
    // Validate required data exists
    if (!method || !method.source || !method.criteria || !method.steps) {
      return <div className="error-message">Verification method data is incomplete</div>;
    }
    
    // Render verification details in structured format
    return (
      <div className="verification-method">
        <div className="method-section">
          <h3>Sources:</h3>
          <ul>
            {Array.isArray(method.source) ? (
              method.source.map((src, index) => (
                <li key={`source-${index}`}>{String(src)}</li>
              ))
            ) : (
              <li>No sources available</li>
            )}
          </ul>
        </div>
        <div className="method-section">
          <h3>Criteria:</h3>
          <ul>
            {Array.isArray(method.criteria) ? (
              method.criteria.map((criterion, index) => (
                <li key={`criteria-${index}`}>{String(criterion)}</li>
              ))
            ) : (
              <li>No criteria available</li>
            )}
          </ul>
        </div>
        <div className="method-section">
          <h3>Steps:</h3>
          <ul>
            {Array.isArray(method.steps) ? (
              method.steps.map((step, index) => (
                <li key={`step-${index}`}>{String(step)}</li>
              ))
            ) : (
              <li>No steps available</li>
            )}
          </ul>
        </div>
      </div>
    );
  };

  // Helper function to render API response or appropriate message
  const renderResponse = () => {
    if (error) {
      return <div className="error-message">{error}</div>;
    }

    if (!response || !response.results || !response.results[0]) {
      return <div className="placeholder">Enter a prediction above and click Send</div>;
    }

    const novaResponse = response.results[0];

    // Render structured response data
    return (
      <div className="structured-response">
        <div className="response-field">
          <h3>Prediction Statement:</h3>
          <p>{novaResponse.prediction_statement}</p>
        </div>
        <div className="response-field">
          <h3>Verification Date:</h3>
          <p>{novaResponse.verification_date}</p>
        </div>
        <div className="response-field">
          <h3>Verification Method:</h3>
          {novaResponse.verification_method && (
            <ErrorBoundary>
              {renderVerificationMethod(novaResponse.verification_method)}
            </ErrorBoundary>
          )}
        </div>
        <div className="response-field">
          <h3>Initial Status:</h3>
          <p>{novaResponse.initial_status}</p>
        </div>
      </div>
    );
  };

  if (isLoading) {
    return (
      <div className="loading" role="status" aria-live="polite">
        Processing your request...
      </div>
    );
  }

  return (
    <ErrorBoundary>
      {renderResponse()}
    </ErrorBoundary>
  );
};

export default PredictionDisplay;