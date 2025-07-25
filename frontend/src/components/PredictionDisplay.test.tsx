import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import PredictionDisplay from './PredictionDisplay';

describe('PredictionDisplay Component', () => {
  const mockResponse = {
    results: [
      {
        prediction_statement: 'Test prediction',
        prediction_date: '2023-12-30',
        verification_date: '2023-12-31',
        verification_method: {
          source: ['Test source'],
          criteria: ['Test criteria'],
          steps: ['Test step']
        },
        initial_status: 'pending'
      }
    ]
  };

  it('shows loading state when isLoading is true', () => {
    render(<PredictionDisplay response={null} error={null} isLoading={true} />);
    expect(screen.getByText('Processing your request...')).toBeInTheDocument();
  });

  it('shows placeholder when no response is available', () => {
    render(<PredictionDisplay response={null} error={null} isLoading={false} />);
    expect(screen.getByText('Enter a prediction above and click Send')).toBeInTheDocument();
  });

  it('shows error message when error is present', () => {
    render(<PredictionDisplay response={null} error="Test error" isLoading={false} />);
    expect(screen.getByText('Test error')).toBeInTheDocument();
  });

  it('renders prediction data correctly', () => {
    render(<PredictionDisplay response={mockResponse} error={null} isLoading={false} />);
    
    expect(screen.getByText('Call Statement:')).toBeInTheDocument();
    expect(screen.getByText('Test prediction')).toBeInTheDocument();
    expect(screen.getByText('Verification Date:')).toBeInTheDocument();
    expect(screen.getByText('2023-12-31')).toBeInTheDocument();
    expect(screen.getByText('Initial Status:')).toBeInTheDocument();
    expect(screen.getByText('pending')).toBeInTheDocument();
    
    // Verification method details
    expect(screen.getByText('Sources:')).toBeInTheDocument();
    expect(screen.getByText('Test source')).toBeInTheDocument();
    expect(screen.getByText('Criteria:')).toBeInTheDocument();
    expect(screen.getByText('Test criteria')).toBeInTheDocument();
    expect(screen.getByText('Steps:')).toBeInTheDocument();
    expect(screen.getByText('Test step')).toBeInTheDocument();
  });

  it('handles incomplete verification method data', () => {
    const incompleteResponse = {
      results: [
        {
          prediction_statement: 'Test prediction',
          prediction_date: '2023-12-30',
          verification_date: '2023-12-31',
          verification_method: {
            source: [],
            criteria: [],
            steps: []
          },
          initial_status: 'pending'
        }
      ]
    };
    
    render(<PredictionDisplay response={incompleteResponse} error={null} isLoading={false} />);
    
    expect(screen.getByText('No data available')).toBeInTheDocument();
  });
});