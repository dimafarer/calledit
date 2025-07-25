import { useState, useEffect } from 'react';
import { APIResponse } from '../types';
import PredictionInput from './PredictionInput';
import PredictionDisplay from './PredictionDisplay';
import LogCallButton from './LogCallButton';
import { getPredictionData, savePredictionData } from '../utils/storageUtils';
import './MakePredictions.css';

/**
 * MakePredictions Component
 * 
 * This component serves as the main interface for users to create new predictions.
 * It orchestrates several child components and manages the prediction data flow:
 * 
 * 1. PredictionInput - For entering prediction text and submitting to the API
 * 2. PredictionDisplay - For showing the structured prediction response
 * 3. LogCallButton - For saving predictions to the database (requires authentication)
 */

interface MakePredictionsProps {
  onNavigateToList: () => void;
}

const MakePredictions: React.FC<MakePredictionsProps> = ({ onNavigateToList }) => {
  // Initialize state with lazy loading from storage
  const [response, setResponse] = useState<APIResponse | null>(() => getPredictionData());
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [prompt, setPrompt] = useState<string>('');

  // Persist response data to storage when it changes
  useEffect(() => {
    if (response !== null) {
      savePredictionData(response);
    }
  }, [response]);

  // Common props for child components to reduce prop drilling
  const commonProps = {
    isLoading,
    setIsLoading,
    setError,
    setResponse,
  };

  return (
    <div className="make-predictions-container">
      <h2>Make a Call</h2>
      
      {/* Log Call Button at the top for mobile visibility */}
      <div className="mobile-buttons-container">
        {response && (
          <LogCallButton
            {...commonProps}
            response={response}
            isVisible={true}
            setPrompt={setPrompt}
            onSuccessfulLog={onNavigateToList}
          />
        )}
      </div>
      
      <PredictionInput 
        {...commonProps}
        prompt={prompt}
        setPrompt={setPrompt}
      />
      
      <div className="response-container">
        <div data-testid="prediction-display">
          <PredictionDisplay
            response={response}
            error={error}
            isLoading={isLoading}
          />
        </div>
        
        {/* Keep the original button for desktop */}
        <div className="desktop-buttons-container" data-testid="log-call-button">
          <LogCallButton
            {...commonProps}
            response={response}
            isVisible={true}
            setPrompt={setPrompt}
            onSuccessfulLog={onNavigateToList}
          />
        </div>
      </div>
    </div>
  );
};

export default MakePredictions;