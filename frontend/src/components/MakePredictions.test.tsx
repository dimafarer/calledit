import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
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
    
    // Check if child components are rendered
    expect(screen.getByTestId('prediction-input')).toBeInTheDocument();
    expect(screen.getByTestId('prediction-display')).toBeInTheDocument();
    expect(screen.getByTestId('log-call-button')).toBeInTheDocument();
    
    // Check if the navigation button is rendered
    expect(screen.getByText('View My Predictions')).toBeInTheDocument();
  });

  it('calls onNavigateToList when the navigation button is clicked', () => {
    render(<MakePredictions onNavigateToList={mockNavigateToList} />);
    
    // Find and click the navigation button
    const navigationButton = screen.getByText('View My Calls');
    fireEvent.click(navigationButton);
    
    // Check if the navigation function was called
    expect(mockNavigateToList).toHaveBeenCalledTimes(1);
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