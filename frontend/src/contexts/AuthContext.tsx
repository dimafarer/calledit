import { createContext, useContext, useEffect, useState, useRef } from 'react';

/**
 * Authentication Context
 * 
 * This module provides authentication functionality for the application using
 * AWS Cognito. It manages the authentication state, handles login/logout flows,
 * and provides access to authentication tokens.
 * 
 * The context exposes:
 * - Current authentication state
 * - Login function that redirects to Cognito
 * - Logout function that clears tokens
 * - Function to retrieve the current ID token
 */

/**
 * AuthContextType Interface
 * 
 * Defines the shape of the authentication context that will be
 * available throughout the application.
 */
interface AuthContextType {
  /** Whether the user is currently authenticated */
  isAuthenticated: boolean;
  
  /** Function to initiate the login flow */
  login: () => void;
  
  /** Function to log the user out */
  logout: () => void;
  
  /** Function to get the current ID token */
  getToken: () => string | null;
}

/**
 * Token storage keys for consistent access to localStorage items
 */
const TOKEN_KEYS = {
  ID: 'idToken',
  ACCESS: 'accessToken',
  REFRESH: 'refreshToken'
};

// Environment variables
const ENV = {
  REGION: import.meta.env.VITE_AWS_REGION,
  CLIENT_ID: import.meta.env.VITE_COGNITO_CLIENT_ID,
  DOMAIN_PREFIX: import.meta.env.VITE_COGNITO_DOMAIN_PREFIX,
  REDIRECT_URI: import.meta.env.DEV 
    ? import.meta.env.VITE_COGNITO_DEV_REDIRECT_URI
    : import.meta.env.VITE_COGNITO_PROD_REDIRECT_URI
};

export const AuthContext = createContext<AuthContextType | undefined>(undefined);

/**
 * AuthProvider Component
 * 
 * This component provides the authentication context to the application.
 * It handles:
 * - Initial authentication state based on stored tokens
 * - Processing authentication code from Cognito redirect
 * - Token exchange with Cognito
 * - Login and logout functionality
 * 
 * @param children - The child components that will have access to the auth context
 */
export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const codeProcessed = useRef(false);
  
  // Cognito domain URL constructed from environment variables
  const cognitoDomain = `https://${ENV.DOMAIN_PREFIX}.auth.${ENV.REGION}.amazoncognito.com`;

  /**
   * Initiates the login flow by redirecting to the Cognito hosted UI
   * 
   * This function constructs the login URL with appropriate parameters
   * and redirects the user's browser to begin the authentication process.
   */
  const login = () => {
    const queryParams = new URLSearchParams({
      client_id: ENV.CLIENT_ID,
      response_type: 'code',
      scope: 'email openid profile',
      redirect_uri: ENV.REDIRECT_URI,
    });
    window.location.href = `${cognitoDomain}/login?${queryParams.toString()}`;
  };

  /**
   * Logs the user out by removing all authentication tokens
   * 
   * This function:
   * 1. Removes all tokens from local storage
   * 2. Updates the authentication state
   */
  const logout = () => {
    Object.values(TOKEN_KEYS).forEach(key => localStorage.removeItem(key));
    setIsAuthenticated(false);
  };

  /**
   * Retrieves the current ID token from local storage
   * 
   * @returns The ID token string or null if not available
   */
  const getToken = () => localStorage.getItem(TOKEN_KEYS.ID);

  /**
   * Exchanges an authorization code for tokens with the Cognito token endpoint
   * 
   * This function:
   * 1. Makes a POST request to the Cognito token endpoint
   * 2. Exchanges the authorization code for ID, access, and refresh tokens
   * 3. Stores the tokens in local storage
   * 4. Updates the authentication state
   * 5. Cleans up the URL by removing the authorization code
   * 
   * @param authCode - The authorization code received from Cognito after login
   */
  const handleTokenExchange = async (authCode: string) => {
    try {
      const tokenEndpoint = `${cognitoDomain}/oauth2/token`;
      const params = new URLSearchParams({
        grant_type: 'authorization_code',
        client_id: ENV.CLIENT_ID,
        code: authCode,
        redirect_uri: ENV.REDIRECT_URI
      });

      const response = await fetch(tokenEndpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: params.toString(),
      });

      const text = await response.text();
      
      if (!response.ok) {
        throw new Error(`Token exchange failed: ${text}`);
      }
      
      const data = JSON.parse(text);
      
      // Store tokens
      localStorage.setItem(TOKEN_KEYS.ID, data.id_token);
      localStorage.setItem(TOKEN_KEYS.ACCESS, data.access_token);
      localStorage.setItem(TOKEN_KEYS.REFRESH, data.refresh_token);
      
      setIsAuthenticated(true);
      
      // Clean up the URL
      window.history.replaceState({}, document.title, window.location.pathname);
    } catch (error) {
      console.error('Authentication error:', error);
    }
  };

  useEffect(() => {
    const urlParams = new URLSearchParams(window.location.search);
    const authCode = urlParams.get('code');
    
    if (authCode && !codeProcessed.current) {
      codeProcessed.current = true;
      handleTokenExchange(authCode);
    } else {
      // Check if we have a stored token
      const token = localStorage.getItem(TOKEN_KEYS.ID);
      if (token) {
        setIsAuthenticated(true);
      }
    }
  }, []);

  return (
    <AuthContext.Provider value={{ isAuthenticated, login, logout, getToken }}>
      {children}
    </AuthContext.Provider>
  );
}

/**
 * Custom hook to access the authentication context
 * 
 * This hook:
 * 1. Accesses the AuthContext using React's useContext
 * 2. Verifies that the hook is being used within an AuthProvider
 * 3. Returns the authentication context with type safety
 * 
 * @returns The authentication context object
 * @throws Error if used outside of an AuthProvider
 */
export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}