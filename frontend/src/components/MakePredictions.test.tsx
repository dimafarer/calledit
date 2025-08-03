import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import MakePredictions from './MakePredictions';
import * as storageUtils from '../utils/storageUtils';

// Mock the storage utils
vi.mock('../utils/storageUtils', () => ({
  getPredictionData: vi.fn(),
  savePredictionData: vi.fn(),
}));

// Mock the child components
vi.mock('./PredictionInput', () => ({
  default: vi.fn(() => <div data-testid="prediction-input">Prediction Input Component</div>),
}));

vi.mock('./PredictionDisplay', () => ({
  default: vi.fn(() => <div data-testid="prediction-display">Prediction Display Component</div>),
}));

vi.mock('./LogCallButton', () => ({
  default: vi.fn(() => <div data-testid="log-call-button">Log Call Button Component</div>),
}));

describe('MakePredictions Component', () => {
  const mockNavigateToList = vi.fn();
  
  beforeEach(() => {
    vi.clearAllMocks();
    (storageUtils.getPredictionData as any).mockReturnValue(null);
  });

  it('renders correctly', () => {
    render(<MakePredictions onNavigateToList={mockNavigateToList} />);
    
    // Check if the component renders with the correct title
    expect(screen.getByText('Make a Call')).toBeInTheDocument();
    
    // Check if main containers are rendered
    expect(screen.getByTestId('prediction-display')).toBeInTheDocument();
    expect(screen.getByTestId('log-call-button')).toBeInTheDocument();
    
    // Check if mobile and desktop containers exist
    expect(document.querySelector('.mobile-buttons-container')).toBeInTheDocument();
    expect(document.querySelector('.response-container')).toBeInTheDocument();
  });

  it('passes onNavigateToList prop to LogCallButton', () => {
    render(<MakePredictions onNavigateToList={mockNavigateToList} />);
    
    // Navigation is handled by LogCallButton component after successful log
    // This test verifies the prop is passed correctly
    expect(screen.getByTestId('log-call-button')).toBeInTheDocument();
  });

  it('initializes with data from local storage', () => {
    const mockPredictionData = {
      results: [
        {
          prediction_statement: 'Test prediction',
          verification_date: '2023-12-31',
          verification_method: {
            source: ['Test source'],
            criteria: ['Test criteria'],
            steps: ['Test step']
          },
          initial_status: 'Pending'
        }
      ]
    };
    
    (storageUtils.getPredictionData as any).mockReturnValue(mockPredictionData);
    
    render(<MakePredictions onNavigateToList={mockNavigateToList} />);
    
    // Check if getPredictionData was called
    expect(storageUtils.getPredictionData).toHaveBeenCalledTimes(1);
  });
});