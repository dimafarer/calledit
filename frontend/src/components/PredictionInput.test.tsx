import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import axios from 'axios';
import PredictionInput from './PredictionInput';


// Mock axios
vi.mock('axios');
const mockedAxios = axios as jest.Mocked<typeof axios>;

// Mock environment variables
vi.stubEnv('VITE_APIGATEWAY', 'https://test-api.example.com');

describe('PredictionInput Component', () => {
  const mockSetResponse = vi.fn();
  const mockSetIsLoading = vi.fn();
  const mockSetError = vi.fn();
  
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders the input field and button', () => {
    render(
      <PredictionInput 
        isLoading={false} 
        setResponse={mockSetResponse}
        setIsLoading={mockSetIsLoading}
        setError={mockSetError}
      />
    );
    
    expect(screen.getByPlaceholderText('Enter your prediction here...')).toBeInTheDocument();
    expect(screen.getByText('Make Call')).toBeInTheDocument();
  });

  it('disables the button when input is empty', () => {
    render(
      <PredictionInput 
        isLoading={false} 
        setResponse={mockSetResponse}
        setIsLoading={mockSetIsLoading}
        setError={mockSetError}
      />
    );
    
    const button = screen.getByText('Make Call');
    expect(button).toBeDisabled();
  });

  it('enables the button when input has text', () => {
    render(
      <PredictionInput 
        isLoading={false} 
        setResponse={mockSetResponse}
        setIsLoading={mockSetIsLoading}
        setError={mockSetError}
      />
    );
    
    const input = screen.getByPlaceholderText('Enter your prediction here...');
    fireEvent.change(input, { target: { value: 'Test prediction' } });
    
    const button = screen.getByText('Make Call');
    expect(button).not.toBeDisabled();
  });

  it('makes API call when button is clicked', async () => {
    // Mock API response
    const mockResponse = {
      data: {
        results: [
          {
            prediction_statement: 'Test prediction',
            verification_date: '2023-12-31',
            verification_method: {
              source: ['Test source'],
              criteria: ['Test criteria'],
              steps: ['Test step']
            },
            initial_status: 'pending'
          }
        ]
      }
    };
    mockedAxios.get.mockResolvedValueOnce(mockResponse);

    render(
      <PredictionInput 
        isLoading={false} 
        setResponse={mockSetResponse}
        setIsLoading={mockSetIsLoading}
        setError={mockSetError}
      />
    );
    
    // Enter text in the input
    const input = screen.getByPlaceholderText('Enter your prediction here...');
    fireEvent.change(input, { target: { value: 'Test input' } });
    
    // Click the submit button
    const submitButton = screen.getByText('Make Call');
    fireEvent.click(submitButton);
    
    // Verify loading state is set
    expect(mockSetIsLoading).toHaveBeenCalledWith(true);
    expect(mockSetError).toHaveBeenCalledWith(null);
    
    // Wait for the API call to complete
    await waitFor(() => {
      expect(mockedAxios.get).toHaveBeenCalledWith(
        'https://test-api.example.com/make-call',
        expect.objectContaining({
          params: { prompt: 'Test input' }
        })
      );
    });
    
    // Verify state updates
    expect(mockSetResponse).toHaveBeenCalledWith(mockResponse.data);
    expect(mockSetIsLoading).toHaveBeenCalledWith(false);
  });

  it('handles API errors correctly', async () => {
    // Mock API error
    mockedAxios.get.mockRejectedValueOnce(new Error('API Error'));
    
    render(
      <PredictionInput 
        isLoading={false} 
        setResponse={mockSetResponse}
        setIsLoading={mockSetIsLoading}
        setError={mockSetError}
      />
    );
    
    // Enter text in the input
    const input = screen.getByPlaceholderText('Enter your prediction here...');
    fireEvent.change(input, { target: { value: 'Test input' } });
    
    // Click the submit button
    const submitButton = screen.getByText('Make Call');
    fireEvent.click(submitButton);
    
    // Wait for the API call to complete
    await waitFor(() => {
      expect(mockSetError).toHaveBeenCalledWith('Error occurred while processing your request');
      expect(mockSetIsLoading).toHaveBeenCalledWith(false);
    });
  });

  it('handles invalid API response format', async () => {
    // Mock invalid API response
    const invalidResponse = {
      data: { results: [] } // Empty results array
    };
    mockedAxios.get.mockResolvedValueOnce(invalidResponse);
    
    render(
      <PredictionInput 
        isLoading={false} 
        setResponse={mockSetResponse}
        setIsLoading={mockSetIsLoading}
        setError={mockSetError}
      />
    );
    
    // Enter text in the input
    const input = screen.getByPlaceholderText('Enter your prediction here...');
    fireEvent.change(input, { target: { value: 'Test input' } });
    
    // Click the submit button
    const submitButton = screen.getByText('Make Call');
    fireEvent.click(submitButton);
    
    // Wait for the API call to complete
    await waitFor(() => {
      expect(mockSetError).toHaveBeenCalledWith('Invalid response format from server');
      expect(mockSetIsLoading).toHaveBeenCalledWith(false);
    });
  });

  it('shows loading state when isLoading is true', () => {
    render(
      <PredictionInput 
        isLoading={true} 
        setResponse={mockSetResponse}
        setIsLoading={mockSetIsLoading}
        setError={mockSetError}
      />
    );
    
    expect(screen.getByText('Generating...')).toBeInTheDocument();
    const button = screen.getByText('Generating...');
    expect(button).toBeDisabled();
  });
});
