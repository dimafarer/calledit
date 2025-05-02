import React, { useState, useEffect } from 'react';
import { APIResponse } from '../types';
import PredictionInput from './PredictionInput';
import PredictionDisplay from './PredictionDisplay';
import LogCallButton from './LogCallButton';
import { getPredictionData, savePredictionData } from '../utils/storageUtils';

interface MakePredictionsProps {
  onNavigateToList: () => void;
}

const MakePredictions: React.FC<MakePredictionsProps> = ({ onNavigateToList }) => {
  // State management using React hooks
  const [response, setResponse] = useState<APIResponse | null>(() => getPredictionData());
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [prompt, setPrompt] = useState('');

  // Save prediction data to local storage whenever it changes
  useEffect(() => {
    savePredictionData(response);
  }, [response]);

  // Custom response setter that updates state and saves to local storage
  const handleSetResponse: React.Dispatch<React.SetStateAction<APIResponse | null>> = (newResponse) => {
    setResponse(newResponse);
    // Note: We don't need to explicitly call savePredictionData here
    // as the useEffect above will handle that
  };

  return (
    <div className="make-predictions-container">
      <h2>Make a Call</h2>
      
      {/* Prediction Input Component */}
      <PredictionInput 
        isLoading={isLoading}
        prompt={prompt}
        setPrompt={setPrompt}
        setResponse={handleSetResponse}
        setIsLoading={setIsLoading}
        setError={setError}
      />
      
      {/* Response display section */}
      <div className="response-container">
        <PredictionDisplay
          response={response}
          error={error}
          isLoading={isLoading}
        />
        
        {/* Buttons container */}
        <div className="buttons-container">
          <LogCallButton
            response={response}
            isLoading={isLoading}
            isVisible={true}
            setIsLoading={setIsLoading}
            setError={setError}
            setResponse={handleSetResponse}
            setPrompt={setPrompt}
          />
          
          {/* Button to navigate to ListPredictions */}
          <button 
            onClick={onNavigateToList}
            className="navigation-button"
            aria-label="View my predictions"
          >
            View My Predictions
          </button>
        </div>
      </div>
    </div>
  );
};

export default MakePredictions;