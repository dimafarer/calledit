import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import App from './App';

// Mock the AuthContext
vi.mock('./contexts/AuthContext', () => ({
  AuthProvider: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  useAuth: () => ({
    isAuthenticated: true,
    login: vi.fn(),
    logout: vi.fn(),
    getToken: vi.fn()
  })
}));
// test
// Mock the components
vi.mock('./components/MakePredictions', () => ({
  default: vi.fn(() => (
    <div data-testid="make-predictions">
      Make Predictions Component
    </div>
  )),
}));

vi.mock('./components/ListPredictions', () => ({
  default: vi.fn(() => (
    <div data-testid="list-predictions">
      List Predictions Component
    </div>
  )),
}));

vi.mock('./components/LoginButton', () => ({
  default: vi.fn(() => <div data-testid="login-button">Login Button</div>),
}));

vi.mock('./components/StreamingCall', () => ({
  default: vi.fn(() => (
    <div data-testid="streaming-call">
      Streaming Call Component
    </div>
  )),
}));

vi.mock('./components/NotificationSettings', () => ({
  default: vi.fn(() => (
    <div data-testid="notification-settings">
      Notification Settings Component
    </div>
  )),
}));

describe('App Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders the application title', () => {
    render(<App />);
    expect(screen.getByText('Called It!!')).toBeInTheDocument();
  });

  it('renders the StreamingCall component by default', () => {
    render(<App />);
    expect(screen.getByTestId('streaming-call')).toBeInTheDocument();
    expect(screen.queryByTestId('list-predictions')).not.toBeInTheDocument();
  });

  it('renders the LoginButton component', () => {
    render(<App />);
    expect(screen.getByTestId('login-button')).toBeInTheDocument();
  });

  it('navigates from StreamingCall to ListPredictions when navigation button is clicked', () => {
    render(<App />);
    
    // Initially shows StreamingCall (default view)
    expect(screen.getByTestId('streaming-call')).toBeInTheDocument();
    
    // Click the navigation button in the header
    fireEvent.click(screen.getByText('📋 View Calls'));
    
    // Now should show ListPredictions
    expect(screen.getByTestId('list-predictions')).toBeInTheDocument();
    expect(screen.queryByTestId('streaming-call')).not.toBeInTheDocument();
  });

  it('navigates from ListPredictions to StreamingCall when navigation button is clicked', () => {
    render(<App />);
    
    // Navigate to ListPredictions first
    fireEvent.click(screen.getByText('📋 View Calls'));
    expect(screen.getByTestId('list-predictions')).toBeInTheDocument();
    
    // Click the navigation button in the header to go back
    fireEvent.click(screen.getByText('⚡ Streaming Mode'));
    
    // Now should show StreamingCall again
    expect(screen.getByTestId('streaming-call')).toBeInTheDocument();
    expect(screen.queryByTestId('list-predictions')).not.toBeInTheDocument();
  });


});