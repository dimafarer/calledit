import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import App from '../App';

// Mock the AuthContext with a controllable isAuthenticated state
const mockLogout = vi.fn();
const mockAuthState = {
  isAuthenticated: true,
  login: vi.fn(),
  logout: mockLogout,
  getToken: vi.fn()
};

vi.mock('../contexts/AuthContext', () => ({
  AuthProvider: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  useAuth: vi.fn(() => mockAuthState)
}));

// Mock the components
vi.mock('./MakePredictions', () => ({
  default: vi.fn(() => (
    <div data-testid="make-predictions">
      Make Predictions Component
    </div>
  )),
}));

vi.mock('./ListPredictions', () => ({
  default: vi.fn(() => (
    <div data-testid="list-predictions">
      List Predictions Component
    </div>
  )),
}));

vi.mock('./LoginButton', () => ({
  default: vi.fn(() => (
    <button 
      data-testid="login-button"
      onClick={mockLogout}
    >
      Logout
    </button>
  )),
}));

vi.mock('./StreamingCall', () => ({
  default: vi.fn(() => (
    <div data-testid="streaming-call">
      Streaming Call Component
    </div>
  )),
}));

vi.mock('./NotificationSettings', () => ({
  default: vi.fn(() => (
    <div data-testid="notification-settings">
      Notification Settings Component
    </div>
  )),
}));

describe('Navigation Controls and Logout Redirection', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockAuthState.isAuthenticated = true; // Reset to authenticated for each test
  });

  it('shows the View My Predictions button when user is authenticated', () => {
    mockAuthState.isAuthenticated = true;
    render(<App />);
    expect(screen.getByText('📋 View Calls')).toBeInTheDocument();
  });

  it('hides the View My Predictions button when user is not authenticated', () => {
    mockAuthState.isAuthenticated = false;
    render(<App />);
    expect(screen.queryByText('📋 View Calls')).not.toBeInTheDocument();
  });

  it('redirects to make predictions screen when user logs out while on list predictions screen', async () => {
    mockAuthState.isAuthenticated = true;
    const { rerender } = render(<App />);
    
    // Navigate to list predictions
    fireEvent.click(screen.getByText('📋 View Calls'));
    expect(screen.getByTestId('list-predictions')).toBeInTheDocument();
    
    // Simulate logout by changing auth state
    mockAuthState.isAuthenticated = false;
    
    // Rerender to trigger the useEffect
    rerender(<App />);
    
    // Should be redirected to streaming call (default view)
    expect(screen.getByTestId('streaming-call')).toBeInTheDocument();
    expect(screen.queryByTestId('list-predictions')).not.toBeInTheDocument();
  });
});