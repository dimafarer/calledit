import { render, screen, act } from '@testing-library/react';
import { AuthProvider, useAuth } from './AuthContext';
import * as authService from '../services/authService';

// Mock the auth service
jest.mock('../services/authService', () => ({
  isAuthenticated: jest.fn(),
  getUser: jest.fn(),
  loginWithCognito: jest.fn(),
  logout: jest.fn(),
}));

// Test component that uses the auth context
const TestComponent = () => {
  const { isLoggedIn, user, login, logout } = useAuth();
  
  return (
    <div>
      <div data-testid="login-status">{isLoggedIn ? 'Logged In' : 'Logged Out'}</div>
      <div data-testid="user-email">{user?.email || 'No User'}</div>
      <button onClick={login} data-testid="login-button">Login</button>
      <button onClick={logout} data-testid="logout-button">Logout</button>
    </div>
  );
};

describe('AuthContext', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });
  
  it('provides authentication status correctly when not authenticated', async () => {
    // Mock isAuthenticated to return false
    jest.spyOn(authService, 'isAuthenticated').mockResolvedValue(false);
    jest.spyOn(authService, 'getUser').mockResolvedValue(null);
    
    await act(async () => {
      render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      );
    });
    
    expect(screen.getByTestId('login-status').textContent).toBe('Logged Out');
    expect(screen.getByTestId('user-email').textContent).toBe('No User');
  });
  
  it('provides authentication status correctly when authenticated', async () => {
    // Mock isAuthenticated to return true
    jest.spyOn(authService, 'isAuthenticated').mockResolvedValue(true);
    jest.spyOn(authService, 'getUser').mockResolvedValue({ email: 'test@example.com' });
    
    await act(async () => {
      render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      );
    });
    
    expect(screen.getByTestId('login-status').textContent).toBe('Logged In');
    expect(screen.getByTestId('user-email').textContent).toBe('test@example.com');
  });
  
  it('calls loginWithCognito when login is called', async () => {
    jest.spyOn(authService, 'isAuthenticated').mockResolvedValue(false);
    jest.spyOn(authService, 'getUser').mockResolvedValue(null);
    
    await act(async () => {
      render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      );
    });
    
    const loginButton = screen.getByTestId('login-button');
    await act(async () => {
      loginButton.click();
    });
    
    expect(authService.loginWithCognito).toHaveBeenCalledTimes(1);
  });
  
  it('calls logout when logout is called', async () => {
    jest.spyOn(authService, 'isAuthenticated').mockResolvedValue(false);
    jest.spyOn(authService, 'getUser').mockResolvedValue(null);
    jest.spyOn(authService, 'logout').mockResolvedValue(undefined);
    
    await act(async () => {
      render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      );
    });
    
    const logoutButton = screen.getByTestId('logout-button');
    await act(async () => {
      logoutButton.click();
    });
    
    expect(authService.logout).toHaveBeenCalledTimes(1);
  });
  
  it('updates auth state when storage event occurs', async () => {
    // Mock isAuthenticated to initially return false
    jest.spyOn(authService, 'isAuthenticated').mockResolvedValue(false);
    jest.spyOn(authService, 'getUser').mockResolvedValue(null);
    
    await act(async () => {
      render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      );
    });
    
    expect(screen.getByTestId('login-status').textContent).toBe('Logged Out');
    
    // Mock isAuthenticated to return true after storage event
    jest.spyOn(authService, 'isAuthenticated').mockResolvedValue(true);
    jest.spyOn(authService, 'getUser').mockResolvedValue({ email: 'test@example.com' });
    
    // Simulate storage event
    await act(async () => {
      window.dispatchEvent(new Event('storage'));
    });
    
    expect(screen.getByTestId('login-status').textContent).toBe('Logged In');
    expect(screen.getByTestId('user-email').textContent).toBe('test@example.com');
  });
});
