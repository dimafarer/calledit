import { APIResponse, VerificationMethod } from '../types';
import ErrorBoundary from './ErrorBoundary';

/**
 * PredictionDisplay Component
 * 
 * This component is responsible for rendering the structured prediction data
 * returned from the API. It handles different states:
 * 
 * - Loading state: Shows a loading indicator
 * - Error state: Displays error messages
 * - Empty state: Shows a placeholder message
 * - Data state: Renders the structured prediction with verification details
 * 
 * The component uses ErrorBoundary to catch and handle any rendering errors
 * that might occur when displaying complex nested data structures.
 */

interface PredictionDisplayProps {
  response: APIResponse | null;
  error: string | null;
  isLoading: boolean;
}

const PredictionDisplay: React.FC<PredictionDisplayProps> = ({ response, error, isLoading }) => {
  /**
   * Renders a list of items with proper key assignment and empty state handling
   * 
   * @param items - Array of items to render as list items
   * @param keyPrefix - Prefix for React key prop to ensure uniqueness
   * @returns React elements representing the list items
   */
  const renderList = (items: any[] | undefined, keyPrefix: string) => {
    if (!Array.isArray(items) || items.length === 0) {
      return <li>No data available</li>;
    }
    
    return items.map((item, index) => (
      <li key={`${keyPrefix}-${index}`}>{String(item)}</li>
    ));
  };
  
  /**
   * Renders a section of the verification method with a title and list of items
   * 
   * @param title - The heading text for the section
   * @param items - Array of items to display in the section
   * @param keyPrefix - Prefix for React keys to ensure uniqueness
   * @returns A structured section with heading and list
   */
  const renderMethodSection = (title: string, items: any[] | undefined, keyPrefix: string) => (
    <div className="method-section">
      <h3>{title}:</h3>
      <ul>{renderList(items, keyPrefix)}</ul>
    </div>
  );

  /**
   * Renders the complete verification method with all its sections
   * 
   * This function validates that all required data is present before rendering
   * and displays an error message if any required data is missing.
   * 
   * @param method - The verification method object containing sources, criteria, and steps
   * @returns The complete verification method UI or an error message
   */
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

  // Add console log to debug the response
  console.log("API Response:", response.results[0]);

  // Valid response state
  const result = response.results[0];
  
  // Handle both prediction_date and creation_date for backward compatibility
  const { 
    prediction_statement, 
    verification_date, 
    verification_method, 
    initial_status,
    timezone = "UTC"
  } = result;
  
  // Use prediction_date if available, otherwise fall back to creation_date
  const utcPredictionDate = result.prediction_date || result.creation_date;
  
  // Convert UTC dates to local timezone for display
  const formatToLocalTime = (utcDateStr: string) => {
    try {
      const date = new Date(utcDateStr);
      return date.toLocaleString();
    } catch (e) {
      return utcDateStr; // Fall back to original string if parsing fails
    }
  };
  
  const predictionDate = formatToLocalTime(utcPredictionDate);
  const localVerificationDate = formatToLocalTime(verification_date);

  return (
    <ErrorBoundary>
      <div className="structured-response">
        <div className="response-field">
          <h3>Prediction Statement:</h3>
          <p>{prediction_statement}</p>
        </div>
        <div className="response-field">
          <h3>Prediction Date:</h3>
          <p>{predictionDate}</p>
        </div>
        <div className="response-field">
          <h3>Verification Date:</h3>
          <p>{localVerificationDate}</p>
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
