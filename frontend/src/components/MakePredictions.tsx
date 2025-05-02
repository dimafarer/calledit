import { useState, useEffect } from 'react';
import { APIResponse } from '../types';
import PredictionInput from './PredictionInput';
import PredictionDisplay from './PredictionDisplay';
import LogCallButton from './LogCallButton';
import { getPredictionData, savePredictionData } from '../utils/storageUtils';
import './MakePredictions.css';

interface MakePredictionsProps {
  onNavigateToList: () => void;
}

const MakePredictions: React.FC<MakePredictionsProps> = ({ onNavigateToList: _onNavigateToList }) => {
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

  // Common props for child components
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
          />
        )}
      </div>
      
      <PredictionInput 
        {...commonProps}
        prompt={prompt}
        setPrompt={setPrompt}
      />
      
      <div className="response-container">
        <PredictionDisplay
          response={response}
          error={error}
          isLoading={isLoading}
        />
        
        {/* Keep the original button for desktop */}
        <div className="desktop-buttons-container">
          <LogCallButton
            {...commonProps}
            response={response}
            isVisible={true}
            setPrompt={setPrompt}
          />
        </div>
      </div>
    </div>
  );
};

export default MakePredictions;