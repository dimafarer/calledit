import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import ListPredictions from './ListPredictions';
import * as apiService from '../services/apiService';
import { AuthContext } from '../contexts/AuthContext';

// Mock the API service
vi.mock('../services/apiService', () => ({
  get: vi.fn()
}));

describe('ListPredictions Component', () => {
  const mockNavigateToMake = vi.fn();
  
  // Mock predictions data
  const mockPredictions = {
    results: [
      {
        prediction_statement: "The price of Bitcoin will exceed $100,000 by December 2023",
        verification_date: "2023-12-31",
        verification_method: {
          source: ["CoinMarketCap", "Binance", "Coinbase"],
          criteria: ["Closing price on any major exchange exceeds $100,000"],
          steps: ["Check price on December 31, 2023", "Document screenshots from multiple exchanges"]
        },
        initial_status: "Pending"
      },
      {
        prediction_statement: "SpaceX will successfully land humans on Mars by 2026",
        verification_date: "2026-12-31",
        verification_method: {
          source: ["NASA", "SpaceX official announcements", "International news coverage"],
          criteria: ["Confirmed human landing on Mars surface", "Live video transmission from Mars"],
          steps: ["Monitor SpaceX launches", "Verify through multiple news sources", "Check official space agency confirmations"]
        },
        initial_status: "Pending"
      }
    ]
  };
  
  // Mock authentication context values
  const mockAuthContextAuthenticated = {
    isAuthenticated: true,
    user: { username: 'testuser' },
    login: vi.fn(),
    logout: vi.fn(),
    loading: false
  };
  
  const mockAuthContextUnauthenticated = {
    isAuthenticated: false,
    user: null,
    login: vi.fn(),
    logout: vi.fn(),
    loading: false
  };
  
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders correctly with loading state when authenticated', async () => {
    // Mock the API call to return a promise that doesn't resolve immediately
    vi.mocked(apiService.get).mockImplementation(() => new Promise(() => {}));
    
    render(
      <AuthContext.Provider value={mockAuthContextAuthenticated}>
        <ListPredictions onNavigateToMake={mockNavigateToMake} />
      </AuthContext.Provider>
    );
    
    // Check if the component renders with the correct title
    expect(screen.getByText('My Predictions')).toBeInTheDocument();
    
    // Check if the navigation button is rendered
    expect(screen.getByText('Make New Prediction')).toBeInTheDocument();
    
    // Check if loading state is displayed
    expect(screen.getByText('Loading your predictions...')).toBeInTheDocument();
  });

  it('calls onNavigateToMake when the navigation button is clicked', () => {
    // Mock the API call
    vi.mocked(apiService.get).mockResolvedValue(mockPredictions);
    
    render(
      <AuthContext.Provider value={mockAuthContextAuthenticated}>
        <ListPredictions onNavigateToMake={mockNavigateToMake} />
      </AuthContext.Provider>
    );
    
    // Find and click the navigation button
    const navigationButton = screen.getByText('Make New Prediction');
    fireEvent.click(navigationButton);
    
    // Check if the navigation function was called
    expect(mockNavigateToMake).toHaveBeenCalledTimes(1);
  });

  it('displays predictions after loading when authenticated', async () => {
    // Mock the API call
    vi.mocked(apiService.get).mockResolvedValue(mockPredictions);
    
    render(
      <AuthContext.Provider value={mockAuthContextAuthenticated}>
        <ListPredictions onNavigateToMake={mockNavigateToMake} />
      </AuthContext.Provider>
    );
    
    await waitFor(() => {
      // Check if the loading message is no longer displayed
      expect(screen.queryByText('Loading your predictions...')).not.toBeInTheDocument();
      
      // Check if predictions are displayed
      expect(screen.getByText('The price of Bitcoin will exceed $100,000 by December 2023')).toBeInTheDocument();
      expect(screen.getByText('SpaceX will successfully land humans on Mars by 2026')).toBeInTheDocument();
    });
  });

  it('displays verification details when expanded', async () => {
    // Mock the API call
    vi.mocked(apiService.get).mockResolvedValue(mockPredictions);
    
    render(
      <AuthContext.Provider value={mockAuthContextAuthenticated}>
        <ListPredictions onNavigateToMake={mockNavigateToMake} />
      </AuthContext.Provider>
    );
    
    await waitFor(() => {
      // Find and click on the details summary to expand
      const detailsSummaries = screen.getAllByText('Verification Method');
      fireEvent.click(detailsSummaries[0]);
      
      // Check if verification details are displayed
      expect(screen.getByText('CoinMarketCap')).toBeInTheDocument();
      expect(screen.getByText('Closing price on any major exchange exceeds $100,000')).toBeInTheDocument();
      expect(screen.getByText('Check price on December 31, 2023')).toBeInTheDocument();
    });
  });
  
  it('shows error message when not authenticated', async () => {
    render(
      <AuthContext.Provider value={mockAuthContextUnauthenticated}>
        <ListPredictions onNavigateToMake={mockNavigateToMake} />
      </AuthContext.Provider>
    );
    
    await waitFor(() => {
      expect(screen.getByText('You must be logged in to view predictions')).toBeInTheDocument();
    });
    
    // API should not be called when not authenticated
    expect(apiService.get).not.toHaveBeenCalled();
  });
  
  it('shows error message when API call fails', async () => {
    // Mock the API call to throw an error
    vi.mocked(apiService.get).mockRejectedValue(new Error('API error'));
    
    render(
      <AuthContext.Provider value={mockAuthContextAuthenticated}>
        <ListPredictions onNavigateToMake={mockNavigateToMake} />
      </AuthContext.Provider>
    );
    
    await waitFor(() => {
      expect(screen.getByText('Failed to load predictions. Please try again later.')).toBeInTheDocument();
    });
  });
  
  it('displays no predictions message when API returns empty results', async () => {
    // Mock the API call to return empty results
    vi.mocked(apiService.get).mockResolvedValue({ results: [] });
    
    render(
      <AuthContext.Provider value={mockAuthContextAuthenticated}>
        <ListPredictions onNavigateToMake={mockNavigateToMake} />
      </AuthContext.Provider>
    );
    
    await waitFor(() => {
      expect(screen.getByText('You haven\'t made any predictions yet.')).toBeInTheDocument();
    });
  });
});