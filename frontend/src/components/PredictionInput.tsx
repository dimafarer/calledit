import React, { useState } from 'react';

interface PredictionInputProps {
  onSubmit: (prompt: string) => void;
  isLoading: boolean;
}

const PredictionInput: React.FC<PredictionInputProps> = ({ onSubmit, isLoading }) => {
  const [prompt, setPrompt] = useState('');

  const handleSubmit = () => {
    if (prompt.trim()) {
      onSubmit(prompt);
    }
  };

  return (
    <>
      <div className="input-container">
        <textarea
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder="Enter your prediction here..."
          rows={4}
          className="text-box"
          aria-label="Prediction input"
        />
      </div>
      <div className="button-container">
        <button 
          onClick={handleSubmit}
          disabled={isLoading || !prompt.trim()}
          className="send-button"
          aria-busy={isLoading}
        >
          {isLoading ? 'Generating...' : 'Make Call'}
        </button>
      </div>
    </>
  );
};

export default PredictionInput;