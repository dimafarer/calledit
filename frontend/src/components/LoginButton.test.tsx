import { render, screen, fireEvent } from '@testing-library/react';
import LoginButton from './LoginButton';
import { AuthProvider } from '../contexts/AuthContext';
import * as authContext from '../contexts/AuthContext';

// Mock the useAuth hook
jest.mock('../contexts/AuthContext', () => ({
  ...jest.requireActual('../contexts/AuthContext'),
  useAuth: jest.fn(),
}));

describe('LoginButton', () => {
  const mockLogin = jest.fn();
  const mockLogout = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders login button when not logged in', () => {
    // Mock the useAuth hook to return not logged in
    jest.spyOn(authContext, 'useAuth').mockReturnValue({
      isLoggedIn: false,
      user: null,
      login: mockLogin,
      logout: mockLogout,
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

  it('renders logout button when logged in', () => {
    // Mock the useAuth hook to return logged in
    jest.spyOn(authContext, 'useAuth').mockReturnValue({
      isLoggedIn: true,
      user: { email: 'test@example.com' },
      login: mockLogin,
      logout: mockLogout,
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
    // Mock the useAuth hook to return not logged in
    jest.spyOn(authContext, 'useAuth').mockReturnValue({
      isLoggedIn: false,
      user: null,
      login: mockLogin,
      logout: mockLogout,
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
    // Mock the useAuth hook to return logged in
    jest.spyOn(authContext, 'useAuth').mockReturnValue({
      isLoggedIn: true,
      user: { email: 'test@example.com' },
      login: mockLogin,
      logout: mockLogout,
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
