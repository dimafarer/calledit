import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import App from './App';

// Mock the AuthContext
vi.mock('./contexts/AuthContext', () => ({
  AuthProvider: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  useAuth: vi.fn(() => ({
    isAuthenticated: true,
    login: vi.fn(),
    logout: vi.fn(),
    getToken: vi.fn()
  }))
}));

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

describe('App Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders the application title', () => {
    render(<App />);
    expect(screen.getByText('Called It!!')).toBeInTheDocument();
  });

  it('renders the MakePredictions component by default', () => {
    render(<App />);
    expect(screen.getByTestId('make-predictions')).toBeInTheDocument();
    expect(screen.queryByTestId('list-predictions')).not.toBeInTheDocument();
  });

  it('renders the LoginButton component', () => {
    render(<App />);
    expect(screen.getByTestId('login-button')).toBeInTheDocument();
  });

  it('navigates from MakePredictions to ListPredictions when navigation button is clicked', () => {
    render(<App />);
    
    // Initially shows MakePredictions
    expect(screen.getByTestId('make-predictions')).toBeInTheDocument();
    
    // Click the navigation button in the header
    fireEvent.click(screen.getByText('View My Predictions'));
    
    // Now should show ListPredictions
    expect(screen.getByTestId('list-predictions')).toBeInTheDocument();
    expect(screen.queryByTestId('make-predictions')).not.toBeInTheDocument();
  });

  it('navigates from ListPredictions to MakePredictions when navigation button is clicked', () => {
    render(<App />);
    
    // Navigate to ListPredictions first
    fireEvent.click(screen.getByText('View My Predictions'));
    expect(screen.getByTestId('list-predictions')).toBeInTheDocument();
    
    // Click the navigation button in the header to go back
    fireEvent.click(screen.getByText('Make New Prediction'));
    
    // Now should show MakePredictions again
    expect(screen.getByTestId('make-predictions')).toBeInTheDocument();
    expect(screen.queryByTestId('list-predictions')).not.toBeInTheDocument();
  });
});