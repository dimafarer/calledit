import React from 'react';
import { NovaResponse } from '../types';

interface LogCallButtonProps {
  onLogCall: () => void;
  isLoading: boolean;
  isVisible: boolean;
}

const LogCallButton: React.FC<LogCallButtonProps> = ({ onLogCall, isLoading, isVisible }) => {
  if (!isVisible) {
    return null;
  }

  return (
    <div className="log-button-container">
      <button 
        onClick={onLogCall}
        disabled={isLoading}
        className="send-button"
        aria-label="Log call data"
        aria-busy={isLoading}
      >
        {isLoading ? 'Logging...' : 'Log Call'}
      </button>
    </div>
  );
};

export default LogCallButton;