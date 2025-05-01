import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import axios from 'axios';
import App from './App';
import { savePredictionData, getPredictionData, clearPredictionData } from './utils/storageUtils';

// Mock axios
vi.mock('axios');
const mockedAxios = axios as jest.Mocked<typeof axios>;

// Mock storage utils
vi.mock('./utils/storageUtils', () => ({
  savePredictionData: vi.fn(),
  getPredictionData: vi.fn(),
  clearPredictionData: vi.fn(),
  STORAGE_KEYS: {
    PREDICTION_DATA: 'calledit_prediction_data'
  }
}));

// Mock environment variables
vi.stubEnv('VITE_APIGATEWAY', 'https://test-api.example.com');

// Mock window.alert
const mockAlert = vi.fn();
window.alert = mockAlert;

describe('App Component', () => {
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
        initial_status: 'pending'
      }
    ]
  };

  beforeEach(() => {
    vi.clearAllMocks();
    // Reset mocked functions
    (getPredictionData as jest.Mock).mockReturnValue(null);
  });

  it('renders the application title', () => {
    render(<App />);
    expect(screen.getByText('Call It!!')).toBeInTheDocument();
  });

  it('initializes with prediction data from local storage if available', () => {
    // Setup: Mock getPredictionData to return stored data
    (getPredictionData as jest.Mock).mockReturnValueOnce(mockPredictionData);
    
    render(<App />);
    
    // Verify the prediction data is displayed
    expect(screen.getByText('Prediction Statement:')).toBeInTheDocument();
    expect(screen.getByText('Test prediction')).toBeInTheDocument();
  });

  it('saves prediction data to local storage when it changes', async () => {
    // Mock API response
    const mockResponse = {
      data: mockPredictionData
    };
    mockedAxios.get.mockResolvedValueOnce(mockResponse);

    render(<App />);
    
    // Enter text in the input
    const input = screen.getByPlaceholderText('Enter your prediction here...');
    fireEvent.change(input, { target: { value: 'Test input' } });
    
    // Click the submit button
    const submitButton = screen.getByText('Make Call');
    fireEvent.click(submitButton);
    
    // Wait for the response to be displayed
    await waitFor(() => {
      expect(screen.getByText('Prediction Statement:')).toBeInTheDocument();
    });
    
    // Verify savePredictionData was called with the correct data
    expect(savePredictionData).toHaveBeenCalledWith(mockPredictionData);
  });

  it('handles form submission correctly', async () => {
    // Mock API response
    const mockResponse = {
      data: mockPredictionData
    };
    mockedAxios.get.mockResolvedValueOnce(mockResponse);

    render(<App />);
    
    // Enter text in the input
    const input = screen.getByPlaceholderText('Enter your prediction here...');
    fireEvent.change(input, { target: { value: 'Test input' } });
    
    // Click the submit button
    const submitButton = screen.getByText('Make Call');
    fireEvent.click(submitButton);
    
    // Wait for the response to be displayed
    await waitFor(() => {
      expect(screen.getByText('Prediction Statement:')).toBeInTheDocument();
      expect(screen.getByText('Test prediction')).toBeInTheDocument();
    });
    
    // Verify API was called correctly
    expect(mockedAxios.get).toHaveBeenCalledWith(
      'https://test-api.example.com/make-call',
      expect.objectContaining({
        params: { prompt: 'Test input' }
      })
    );
  });

  it('handles log call button correctly and clears local storage after successful log', async () => {
    // Mock API responses
    const getMockResponse = {
      data: mockPredictionData
    };
    const postMockResponse = {
      data: {
        response: 'Prediction logged successfully'
      }
    };
    
    mockedAxios.get.mockResolvedValueOnce(getMockResponse);
    mockedAxios.post.mockResolvedValueOnce(postMockResponse);

    render(<App />);
    
    // Enter text and submit
    const input = screen.getByPlaceholderText('Enter your prediction here...');
    fireEvent.change(input, { target: { value: 'Test input' } });
    
    const submitButton = screen.getByText('Make Call');
    fireEvent.click(submitButton);
    
    // Wait for the response and log call button to appear
    await waitFor(() => {
      expect(screen.getByText('Log Call')).toBeInTheDocument();
    });
    
    // Click the log call button
    const logButton = screen.getByText('Log Call');
    fireEvent.click(logButton);
    
    // Verify the POST request was made correctly
    await waitFor(() => {
      expect(mockedAxios.post).toHaveBeenCalledWith(
        'https://test-api.example.com/log-call',
        {
          prediction: mockPredictionData.results[0]
        },
        expect.objectContaining({
          headers: {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
          }
        })
      );
    });
    
    // Verify clearPredictionData was called after successful log
    expect(clearPredictionData).toHaveBeenCalled();
    
    // Verify alert was shown
    expect(mockAlert).toHaveBeenCalledWith('Prediction logged successfully!');
  });

  it('handles API errors correctly', async () => {
    // Mock API error
    mockedAxios.get.mockRejectedValueOnce(new Error('API Error'));
    
    render(<App />);
    
    // Enter text and submit
    const input = screen.getByPlaceholderText('Enter your prediction here...');
    fireEvent.change(input, { target: { value: 'Test input' } });
    
    const submitButton = screen.getByText('Make Call');
    fireEvent.click(submitButton);
    
    // Wait for error message
    await waitFor(() => {
      expect(screen.getByText('Error occurred while processing your request')).toBeInTheDocument();
    });
  });

  it('handles log call API errors correctly', async () => {
    // Mock API responses
    const getMockResponse = {
      data: mockPredictionData
    };
    
    mockedAxios.get.mockResolvedValueOnce(getMockResponse);
    mockedAxios.post.mockRejectedValueOnce(new Error('Log API Error'));

    render(<App />);
    
    // Enter text and submit
    const input = screen.getByPlaceholderText('Enter your prediction here...');
    fireEvent.change(input, { target: { value: 'Test input' } });
    
    const submitButton = screen.getByText('Make Call');
    fireEvent.click(submitButton);
    
    // Wait for the response and log call button to appear
    await waitFor(() => {
      expect(screen.getByText('Log Call')).toBeInTheDocument();
    });
    
    // Click the log call button
    const logButton = screen.getByText('Log Call');
    fireEvent.click(logButton);
    
    // Wait for error message
    await waitFor(() => {
      expect(screen.getByText('Error occurred while logging your prediction')).toBeInTheDocument();
    });
    
    // Verify clearPredictionData was NOT called after failed log
    expect(clearPredictionData).not.toHaveBeenCalled();
  });

  it('renders the login button and toggles state when clicked', async () => {
    render(<App />);
    
    // Check if login button is rendered
    const loginButton = screen.getByText('Login');
    expect(loginButton).toBeInTheDocument();
    
    // Click the login button to toggle state
    fireEvent.click(loginButton);
    
    // Check if button text changed to "Logout"
    expect(screen.getByText('Logout')).toBeInTheDocument();
    
    // Click again to toggle back
    fireEvent.click(screen.getByText('Logout'));
    
    // Check if button text changed back to "Login"
    expect(screen.getByText('Login')).toBeInTheDocument();
  });
});