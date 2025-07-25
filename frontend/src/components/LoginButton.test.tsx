import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import LoginButton from './LoginButton';
import { AuthProvider } from '../contexts/AuthContext';
import * as authContext from '../contexts/AuthContext';

// Mock the useAuth hook
vi.mock('../contexts/AuthContext', async () => {
  const actual = await vi.importActual('../contexts/AuthContext');
  return {
    ...actual,
    useAuth: vi.fn(),
  };
});

describe('LoginButton', () => {
  const mockLogin = vi.fn();
  const mockLogout = vi.fn();
  const mockGetToken = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders login button when not authenticated', () => {
    // Mock the useAuth hook to return not authenticated
    vi.spyOn(authContext, 'useAuth').mockReturnValue({
      isAuthenticated: false,
      login: mockLogin,
      logout: mockLogout,
      getToken: mockGetToken,
    });

    render(
      <AuthProvider>
        <LoginButton />
      </AuthProvider>
    );
    
    const buttonElement = screen.getByRole('button', { name: /login/i });
    expect(buttonElement).toBeInTheDocument();
    expect(buttonElement.textContent).toBe('Login');
  });

  it('renders logout button when authenticated', () => {
    // Mock the useAuth hook to return authenticated
    vi.spyOn(authContext, 'useAuth').mockReturnValue({
      isAuthenticated: true,
      login: mockLogin,
      logout: mockLogout,
      getToken: mockGetToken,
    });

    render(
      <AuthProvider>
        <LoginButton />
      </AuthProvider>
    );
    
    const buttonElement = screen.getByRole('button', { name: /logout/i });
    expect(buttonElement).toBeInTheDocument();
    expect(buttonElement.textContent).toBe('Logout');
  });

  it('calls login function when login button is clicked', () => {
    // Mock the useAuth hook to return not authenticated
    vi.spyOn(authContext, 'useAuth').mockReturnValue({
      isAuthenticated: false,
      login: mockLogin,
      logout: mockLogout,
      getToken: mockGetToken,
    });

    render(
      <AuthProvider>
        <LoginButton />
      </AuthProvider>
    );
    
    const buttonElement = screen.getByRole('button', { name: /login/i });
    fireEvent.click(buttonElement);
    
    expect(mockLogin).toHaveBeenCalledTimes(1);
    expect(mockLogout).not.toHaveBeenCalled();
  });

  it('calls logout function when logout button is clicked', () => {
    // Mock the useAuth hook to return authenticated
    vi.spyOn(authContext, 'useAuth').mockReturnValue({
      isAuthenticated: true,
      login: mockLogin,
      logout: mockLogout,
      getToken: mockGetToken,
    });

    render(
      <AuthProvider>
        <LoginButton />
      </AuthProvider>
    );
    
    const buttonElement = screen.getByRole('button', { name: /logout/i });
    fireEvent.click(buttonElement);
    
    expect(mockLogout).toHaveBeenCalledTimes(1);
    expect(mockLogin).not.toHaveBeenCalled();
  });
});