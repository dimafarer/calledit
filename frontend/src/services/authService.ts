// Comment out the Auth import since it's causing issues
// import { Auth } from 'aws-amplify';

// Constants for local storage keys
const TOKEN_KEY = 'cognito_token';
const REFRESH_TOKEN_KEY = 'cognito_refresh_token';
const ID_TOKEN_KEY = 'cognito_id_token';

// Interface for authentication response
export interface AuthResponse {
  accessToken: string;
  idToken: string;
  refreshToken: string;
  expiresIn: number;
}

// Interface for token storage
export interface TokenStorage {
  accessToken: string;
  idToken: string;
  refreshToken: string;
  expiresAt: number;
}

/**
 * Handles the redirect from Cognito Hosted UI
 * Extracts the authorization code from the URL and exchanges it for tokens
 */
export const handleAuthRedirect = async (): Promise<AuthResponse | null> => {
  try {
    // Get the current URL
    const urlParams = new URLSearchParams(window.location.search);
    const code = urlParams.get('code');
    
    if (!code) {
      return null;
    }
    
    // Exchange the code for tokens
    const redirectUri = window.location.origin;
    const response = await fetch('/api/auth/token', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ code, redirectUri }),
    });
    
    if (!response.ok) {
      throw new Error('Failed to exchange code for tokens');
    }
    
    const tokens = await response.json();
    
    // Store tokens
    storeTokens(tokens);
    
    // Clean up the URL
    window.history.replaceState({}, document.title, window.location.pathname);
    
    return tokens;
  } catch (error) {
    console.error('Error handling authentication redirect:', error);
    return null;
  }
};

/**
 * Redirects the user to the Cognito Hosted UI for login
 */
export const loginWithCognito = async () => {
  try {
    // Get the Cognito domain and client ID from environment variables or config
    const cognitoDomain = import.meta.env.VITE_COGNITO_DOMAIN || '';
    const clientId = import.meta.env.VITE_COGNITO_CLIENT_ID || '';
    const redirectUri = window.location.origin;
    
    // Construct the Cognito Hosted UI URL
    const loginUrl = `${cognitoDomain}/login?client_id=${clientId}&response_type=code&scope=email+openid+profile&redirect_uri=${encodeURIComponent(redirectUri)}`;
    
    // Redirect to the Cognito Hosted UI
    window.location.href = loginUrl;
  } catch (error) {
    console.error('Error initiating login:', error);
  }
};

/**
 * Logs the user out by clearing tokens and redirecting to Cognito logout endpoint
 */
export const logout = async () => {
  try {
    // Clear tokens from local storage
    clearTokens();
    
    // Get the Cognito domain and client ID from environment variables or config
    const cognitoDomain = import.meta.env.VITE_COGNITO_DOMAIN || '';
    const clientId = import.meta.env.VITE_COGNITO_CLIENT_ID || '';
    const redirectUri = window.location.origin;
    
    // Construct the Cognito logout URL
    const logoutUrl = `${cognitoDomain}/logout?client_id=${clientId}&logout_uri=${encodeURIComponent(redirectUri)}`;
    
    // Redirect to the Cognito logout endpoint
    window.location.href = logoutUrl;
  } catch (error) {
    console.error('Error signing out:', error);
    // Still clear local tokens even if the remote signout fails
    clearTokens();
  }
};

/**
 * Stores authentication tokens in local storage
 */
export const storeTokens = (tokens: AuthResponse): void => {
  const expiresAt = Date.now() + tokens.expiresIn * 1000;
  
  // Store tokens in local storage
  localStorage.setItem(TOKEN_KEY, tokens.accessToken);
  localStorage.setItem(ID_TOKEN_KEY, tokens.idToken);
  localStorage.setItem(REFRESH_TOKEN_KEY, tokens.refreshToken);
  localStorage.setItem('token_expires_at', expiresAt.toString());
};

/**
 * Clears authentication tokens from local storage
 */
export const clearTokens = (): void => {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(ID_TOKEN_KEY);
  localStorage.removeItem(REFRESH_TOKEN_KEY);
  localStorage.removeItem('token_expires_at');
};

/**
 * Gets the current access token from local storage
 */
export const getAccessToken = async (): Promise<string | null> => {
  try {
    const token = localStorage.getItem(TOKEN_KEY);
    
    if (!token) {
      console.warn('No access token found in local storage');
      return null;
    }
    
    // Check if token is expired
    const expiresAt = localStorage.getItem('token_expires_at');
    if (expiresAt && Date.now() >= parseInt(expiresAt, 10)) {
      console.warn('Access token has expired');
      return null;
    }
    
    return token;
  } catch (error) {
    console.error('Error getting access token:', error);
    return null;
  }
};

/**
 * Gets the current ID token from local storage
 */
export const getIdToken = async (): Promise<string | null> => {
  try {
    return localStorage.getItem(ID_TOKEN_KEY);
  } catch (error) {
    console.error('Error getting ID token:', error);
    return null;
  }
};

/**
 * Checks if the user is authenticated
 */
export const isAuthenticated = async (): Promise<boolean> => {
  try {
    // Fall back to local storage check
    const token = localStorage.getItem(TOKEN_KEY);
    const expiresAt = localStorage.getItem('token_expires_at');
    
    if (!token || !expiresAt) {
      return false;
    }
    
    return Date.now() < parseInt(expiresAt, 10);
  } catch (error) {
    console.error('Error checking authentication status:', error);
    return false;
  }
};

/**
 * Gets the authenticated user information
 */
export const getUser = async (): Promise<any> => {
  try {
    // Fall back to decoding the ID token
    const idToken = localStorage.getItem(ID_TOKEN_KEY);
    
    if (!idToken) {
      return null;
    }
    
    try {
      // Decode the JWT token
      const base64Url = idToken.split('.')[1];
      const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
      const jsonPayload = decodeURIComponent(
        atob(base64)
          .split('')
          .map((c) => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
          .join('')
      );
      
      return JSON.parse(jsonPayload);
    } catch (error) {
      console.error('Error decoding ID token:', error);
      return null;
    }
  } catch (error) {
    console.error('Error getting user:', error);
    return null;
  }
};



