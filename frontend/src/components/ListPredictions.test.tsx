import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import ListPredictions from './ListPredictions';

describe('ListPredictions Component', () => {
  const mockNavigateToMake = vi.fn();
  
  beforeEach(() => {
    vi.clearAllMocks();
    // Reset timers before each test
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('renders correctly with loading state', () => {
    render(<ListPredictions onNavigateToMake={mockNavigateToMake} />);
    
    // Check if the component renders with the correct title
    expect(screen.getByText('My Predictions')).toBeInTheDocument();
    
    // Check if the navigation button is rendered
    expect(screen.getByText('Make New Prediction')).toBeInTheDocument();
    
    // Check if loading state is displayed
    expect(screen.getByText('Loading your predictions...')).toBeInTheDocument();
  });

  it('calls onNavigateToMake when the navigation button is clicked', () => {
    render(<ListPredictions onNavigateToMake={mockNavigateToMake} />);
    
    // Find and click the navigation button
    const navigationButton = screen.getByText('Make New Prediction');
    fireEvent.click(navigationButton);
    
    // Check if the navigation function was called
    expect(mockNavigateToMake).toHaveBeenCalledTimes(1);
  });

  it('displays predictions after loading', async () => {
    render(<ListPredictions onNavigateToMake={mockNavigateToMake} />);
    
    // Fast-forward time to complete the loading
    vi.advanceTimersByTime(1000);
    
    await waitFor(() => {
      // Check if the loading message is no longer displayed
      expect(screen.queryByText('Loading your predictions...')).not.toBeInTheDocument();
      
      // Check if predictions are displayed
      expect(screen.getByText('The price of Bitcoin will exceed $100,000 by December 2023')).toBeInTheDocument();
      expect(screen.getByText('SpaceX will successfully land humans on Mars by 2026')).toBeInTheDocument();
      expect(screen.getByText('Artificial General Intelligence will be achieved by 2030')).toBeInTheDocument();
    });
  });

  it('displays verification details when expanded', async () => {
    render(<ListPredictions onNavigateToMake={mockNavigateToMake} />);
    
    // Fast-forward time to complete the loading
    vi.advanceTimersByTime(1000);
    
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
});