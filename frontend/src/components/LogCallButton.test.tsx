import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import axios from 'axios';
import LogCallButton from './LogCallButton';
import { APIResponse } from '../types';
import * as AuthContext from '../contexts/AuthContext';

// Mock axios
vi.mock('axios');
const mockedAxios = axios as jest.Mocked<typeof axios>;

// Mock window.alert
const mockAlert = vi.fn();
window.alert = mockAlert;

// Mock AuthContext
vi.mock('../contexts/AuthContext', () => ({
  useAuth: vi.fn()
}));

// Mock environment variables
vi.stubEnv('VITE_APIGATEWAY', 'https://test-api.example.com');

describe('LogCallButton Component', () => {
  const mockSetIsLoading = vi.fn();
  const mockSetError = vi.fn();
  const mockSetResponse = vi.fn();
  const mockSetPrompt = vi.fn();
  const mockGetToken = vi.fn().mockReturnValue('mock-token');
  const mockResponse: APIResponse = {
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
  
  beforeEach(() => {
    vi.clearAllMocks();
    // Default mock for useAuth - authenticated
    vi.mocked(AuthContext.useAuth).mockReturnValue({
      isAuthenticated: true,
      login: vi.fn(),
      logout: vi.fn(),
      getToken: mockGetToken
    });
  });

  it('renders nothing when isVisible is false', () => {
    const { container } = render(
      <LogCallButton 
        response={mockResponse}
        isLoading={false} 
        isVisible={false}
        setIsLoading={mockSetIsLoading}
        setError={mockSetError}
        setResponse={mockSetResponse}
        setPrompt={mockSetPrompt}
      />
    );
    
    expect(container.firstChild).toBeNull();
  });

  it('renders the button when isVisible is true', () => {
    render(
      <LogCallButton 
        response={mockResponse}
        isLoading={false} 
        isVisible={true}
        setIsLoading={mockSetIsLoading}
        setError={mockSetError}
        setResponse={mockSetResponse}
        setPrompt={mockSetPrompt}
      />
    );
    
    expect(screen.getByText('Log Call')).toBeInTheDocument();
  });

  it('renders the button as disabled when no valid response data is available', () => {
    render(
      <LogCallButton 
        response={null}
        isLoading={false} 
        isVisible={true}
        setIsLoading={mockSetIsLoading}
        setError={mockSetError}
        setResponse={mockSetResponse}
        setPrompt={mockSetPrompt}
      />
    );
    
    const button = screen.getByText('Log Call');
    expect(button).toBeDisabled();
    expect(button).toHaveAttribute('title', 'Make a call first');
  });

  it('renders the button as disabled when user is not authenticated', () => {
    // Mock unauthenticated state
    vi.mocked(AuthContext.useAuth).mockReturnValue({
      isAuthenticated: false,
      login: vi.fn(),
      logout: vi.fn(),
      getToken: vi.fn().mockReturnValue(null)
    });

    render(
      <LogCallButton 
        response={mockResponse}
        isLoading={false} 
        isVisible={true}
        setIsLoading={mockSetIsLoading}
        setError={mockSetError}
        setResponse={mockSetResponse}
        setPrompt={mockSetPrompt}
      />
    );
    
    const button = screen.getByText('Log Call');
    expect(button).toBeDisabled();
    expect(button).toHaveAttribute('title', 'Log in first');
  });

  it('renders the button as disabled when both prediction and authentication are missing', () => {
    // Mock unauthenticated state
    vi.mocked(AuthContext.useAuth).mockReturnValue({
      isAuthenticated: false,
      login: vi.fn(),
      logout: vi.fn(),
      getToken: vi.fn().mockReturnValue(null)
    });

    render(
      <LogCallButton 
        response={null}
        isLoading={false} 
        isVisible={true}
        setIsLoading={mockSetIsLoading}
        setError={mockSetError}
        setResponse={mockSetResponse}
        setPrompt={mockSetPrompt}
      />
    );
    
    const button = screen.getByText('Log Call');
    expect(button).toBeDisabled();
    expect(button).toHaveAttribute('title', 'Make a call and log in first');
  });

  it('shows error message when clicked with no valid response data', () => {
    render(
      <LogCallButton 
        response={null}
        isLoading={false} 
        isVisible={true}
        setIsLoading={mockSetIsLoading}
        setError={mockSetError}
        setResponse={mockSetResponse}
        setPrompt={mockSetPrompt}
      />
    );
    
    // Try to click the button (even though it's disabled)
    const logButton = screen.getByText('Log Call');
    fireEvent.click(logButton);
    
    // Verify error message is set
    expect(mockSetError).toHaveBeenCalledWith('No call data available to log. Please make a call first.');
  });

  it('shows error message when clicked with valid response but not authenticated', () => {
    // Mock unauthenticated state
    vi.mocked(AuthContext.useAuth).mockReturnValue({
      isAuthenticated: false,
      login: vi.fn(),
      logout: vi.fn(),
      getToken: vi.fn().mockReturnValue(null)
    });

    render(
      <LogCallButton 
        response={mockResponse}
        isLoading={false} 
        isVisible={true}
        setIsLoading={mockSetIsLoading}
        setError={mockSetError}
        setResponse={mockSetResponse}
        setPrompt={mockSetPrompt}
      />
    );
    
    // Try to click the button (even though it's disabled)
    const logButton = screen.getByText('Log Call');
    fireEvent.click(logButton);
    
    // Verify error message is set
    expect(mockSetError).toHaveBeenCalledWith('You must be logged in to log a call.');
  });

  it('makes API call with auth token when button is clicked', async () => {
    // Mock API response
    const postMockResponse = {
      data: {
        response: 'Prediction logged successfully'
      }
    };
    mockedAxios.post.mockResolvedValueOnce(postMockResponse);

    render(
      <LogCallButton 
        response={mockResponse}
        isLoading={false} 
        isVisible={true}
        setIsLoading={mockSetIsLoading}
        setError={mockSetError}
        setResponse={mockSetResponse}
        setPrompt={mockSetPrompt}
      />
    );
    
    // Click the log call button
    const logButton = screen.getByText('Log Call');
    fireEvent.click(logButton);
    
    // Verify loading state is set
    expect(mockSetIsLoading).toHaveBeenCalledWith(true);
    expect(mockSetError).toHaveBeenCalledWith(null);
    
    // Wait for the API call to complete
    await waitFor(() => {
      expect(mockedAxios.post).toHaveBeenCalledWith(
        'https://test-api.example.com/log-call',
        {
          prediction: mockResponse.results[0]
        },
        expect.objectContaining({
          headers: {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'Authorization': 'Bearer mock-token'
          }
        })
      );
    });
    
    // Verify response state is cleared
    expect(mockSetResponse).toHaveBeenCalledWith(null);
    
    // Verify prompt is cleared
    expect(mockSetPrompt).toHaveBeenCalledWith('');
    
    // Verify alert was shown and loading state was updated
    expect(mockAlert).toHaveBeenCalledWith('Call logged successfully!');
    expect(mockSetIsLoading).toHaveBeenCalledWith(false);
  });

  it('handles API errors correctly', async () => {
    // Mock API error
    mockedAxios.post.mockRejectedValueOnce(new Error('API Error'));
    
    render(
      <LogCallButton 
        response={mockResponse}
        isLoading={false} 
        isVisible={true}
        setIsLoading={mockSetIsLoading}
        setError={mockSetError}
        setResponse={mockSetResponse}
        setPrompt={mockSetPrompt}
      />
    );
    
    // Click the log call button
    const logButton = screen.getByText('Log Call');
    fireEvent.click(logButton);
    
    // Wait for the API call to complete
    await waitFor(() => {
      expect(mockSetError).toHaveBeenCalledWith('Error occurred while logging your call');
      expect(mockSetIsLoading).toHaveBeenCalledWith(false);
    });
    
    // Verify prompt is not cleared on error
    expect(mockSetPrompt).not.toHaveBeenCalled();
  });

  it('shows loading state when isLoading is true', () => {
    render(
      <LogCallButton 
        response={mockResponse}
        isLoading={true} 
        isVisible={true}
        setIsLoading={mockSetIsLoading}
        setError={mockSetError}
        setResponse={mockSetResponse}
        setPrompt={mockSetPrompt}
      />
    );
    
    expect(screen.getByText('Logging...')).toBeInTheDocument();
    const button = screen.getByText('Logging...');
    expect(button).toBeDisabled();
  });
});