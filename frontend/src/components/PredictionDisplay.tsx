import { APIResponse, VerificationMethod } from '../types';
import ErrorBoundary from './ErrorBoundary';

interface PredictionDisplayProps {
  response: APIResponse | null;
  error: string | null;
  isLoading: boolean;
}

const PredictionDisplay: React.FC<PredictionDisplayProps> = ({ response, error, isLoading }) => {
  // Render list items from array data
  const renderList = (items: any[] | undefined, keyPrefix: string) => {
    if (!Array.isArray(items) || items.length === 0) {
      return <li>No data available</li>;
    }
    
    return items.map((item, index) => (
      <li key={`${keyPrefix}-${index}`}>{String(item)}</li>
    ));
  };
  
  // Render verification method section
  const renderMethodSection = (title: string, items: any[] | undefined, keyPrefix: string) => (
    <div className="method-section">
      <h3>{title}:</h3>
      <ul>{renderList(items, keyPrefix)}</ul>
    </div>
  );

  // Render verification method details
  const renderVerificationMethod = (method: VerificationMethod) => {
    if (!method || !method.source || !method.criteria || !method.steps) {
      return <div className="error-message">Verification method data is incomplete</div>;
    }
    
    return (
      <div className="verification-method">
        {renderMethodSection('Sources', method.source, 'source')}
        {renderMethodSection('Criteria', method.criteria, 'criteria')}
        {renderMethodSection('Steps', method.steps, 'step')}
      </div>
    );
  };

  // Loading state
  if (isLoading) {
    return (
      <div className="loading" role="status" aria-live="polite">
        Processing your request...
      </div>
    );
  }
  
  // Error state
  if (error) {
    return <div className="error-message">{error}</div>;
  }

  // Empty or invalid response state
  if (!response?.results?.[0]) {
    return <div className="placeholder">Enter a prediction above and click Send</div>;
  }

  // Valid response state
  const { 
    prediction_statement, 
    verification_date, 
    verification_method, 
    initial_status 
  } = response.results[0];

  return (
    <ErrorBoundary>
      <div className="structured-response">
        <div className="response-field">
          <h3>Prediction Statement:</h3>
          <p>{prediction_statement}</p>
        </div>
        <div className="response-field">
          <h3>Verification Date:</h3>
          <p>{verification_date}</p>
        </div>
        <div className="response-field">
          <h3>Verification Method:</h3>
          {verification_method && (
            <ErrorBoundary>
              {renderVerificationMethod(verification_method)}
            </ErrorBoundary>
          )}
        </div>
        <div className="response-field">
          <h3>Initial Status:</h3>
          <p>{initial_status}</p>
        </div>
      </div>
    </ErrorBoundary>
  );
};

export default PredictionDisplay;
