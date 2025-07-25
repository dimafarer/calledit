import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, act } from '@testing-library/react';
import { AuthProvider, useAuth } from './AuthContext';

// Test component that uses the auth context
const TestComponent = () => {
  const { isAuthenticated, login, logout, getToken } = useAuth();
  
  return (
    <div>
      <div data-testid="auth-status">{isAuthenticated ? 'Authenticated' : 'Not Authenticated'}</div>
      <div data-testid="token">{getToken() || 'No Token'}</div>
      <button onClick={login} data-testid="login-button">Login</button>
      <button onClick={logout} data-testid="logout-button">Logout</button>
    </div>
  );
};

// Mock localStorage
const localStorageMock = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: vi.fn((key: string) => store[key] || null),
    setItem: vi.fn((key: string, value: string) => {
      store[key] = value;
    }),
    removeItem: vi.fn((key: string) => {
      delete store[key];
    }),
    clear: vi.fn(() => {
      store = {};
    }),
  };
})();

// Replace the global localStorage with our mock
Object.defineProperty(window, 'localStorage', {
  value: localStorageMock,
});

// Mock window.location
const originalLocation = window.location;
Object.defineProperty(window, 'location', {
  writable: true,
  value: {
    href: '',
    pathname: '/',
    search: '',
    hash: '',
    replace: vi.fn(),
    reload: vi.fn(),
    assign: vi.fn(),
  },
});

describe('AuthContext', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorageMock.clear();
    window.location.href = '';
    window.location.search = '';
  });
  
  afterAll(() => {
    // Restore original location
    Object.defineProperty(window, 'location', {
      writable: true,
      value: originalLocation,
    });
  });
  
  it('provides authentication status correctly when not authenticated', () => {
    render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    );
    
    expect(screen.getByTestId('auth-status').textContent).toBe('Not Authenticated');
    expect(screen.getByTestId('token').textContent).toBe('No Token');
  });
  
  it('provides authentication status correctly when authenticated', () => {
    // Setup: Add token to localStorage store directly
    localStorageMock.setItem('idToken', 'mock-token');
    localStorageMock.getItem.mockImplementation((key: string) => {
      if (key === 'idToken') return 'mock-token';
      return null;
    });
    
    render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    );
    
    expect(screen.getByTestId('auth-status').textContent).toBe('Authenticated');
  });
  
  it('redirects to Cognito login when login is called', () => {
    render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    );
    
    const loginButton = screen.getByTestId('login-button');
    act(() => {
      loginButton.click();
    });
    
    expect(window.location.href).toContain('amazoncognito.com/login');
  });
  
  it('clears tokens when logout is called', () => {
    // Setup: Add tokens to localStorage
    localStorageMock.setItem('idToken', 'mock-id-token');
    localStorageMock.setItem('accessToken', 'mock-access-token');
    localStorageMock.setItem('refreshToken', 'mock-refresh-token');
    
    render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    );
    
    const logoutButton = screen.getByTestId('logout-button');
    act(() => {
      logoutButton.click();
    });
    
    expect(localStorageMock.removeItem).toHaveBeenCalledWith('idToken');
    expect(localStorageMock.removeItem).toHaveBeenCalledWith('accessToken');
    expect(localStorageMock.removeItem).toHaveBeenCalledWith('refreshToken');
    expect(screen.getByTestId('auth-status').textContent).toBe('Not Authenticated');
  });
});