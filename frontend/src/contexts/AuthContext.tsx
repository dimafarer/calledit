import { createContext, useContext, useEffect, useState, useRef } from 'react';

/**
 * AuthContextType Interface
 */
interface AuthContextType {
  isAuthenticated: boolean;
  login: () => void;
  logout: () => void;
  getToken: () => string | null;
}

/**
 * Token storage keys for consistent access to localStorage items
 */
const TOKEN_KEYS = {
  ID: 'idToken',
  ACCESS: 'accessToken',
  REFRESH: 'refreshToken',
  EXPIRY: 'tokenExpiry'
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

// Create context with undefined default value
const AuthContext = createContext<AuthContextType | undefined>(undefined);

// AuthProvider component
function AuthProvider({ children }: { children: React.ReactNode }) {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const codeProcessed = useRef(false);
  
  const cognitoDomain = `https://${ENV.DOMAIN_PREFIX}.auth.${ENV.REGION}.amazoncognito.com`;

  const login = () => {
    const queryParams = new URLSearchParams({
      client_id: ENV.CLIENT_ID,
      response_type: 'code',
      scope: 'email openid profile',
      redirect_uri: ENV.REDIRECT_URI,
    });
    window.location.href = `${cognitoDomain}/login?${queryParams.toString()}&cookie_consent=true`;
  };

  const logout = () => {
    Object.values(TOKEN_KEYS).forEach(key => localStorage.removeItem(key));
    setIsAuthenticated(false);
  };

  const getToken = () => localStorage.getItem(TOKEN_KEYS.ID);

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
      
      // Store tokens with expiry
      const expiresIn = data.expires_in || 86400;
      const expiryTime = Date.now() + (expiresIn * 1000) - (5 * 60 * 1000);
      
      localStorage.setItem(TOKEN_KEYS.ID, data.id_token);
      localStorage.setItem(TOKEN_KEYS.ACCESS, data.access_token);
      localStorage.setItem(TOKEN_KEYS.REFRESH, data.refresh_token);
      localStorage.setItem(TOKEN_KEYS.EXPIRY, expiryTime.toString());
      
      setIsAuthenticated(true);
      
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
      // Check if we have a valid token
      const token = localStorage.getItem(TOKEN_KEYS.ID);
      const expiry = localStorage.getItem(TOKEN_KEYS.EXPIRY);
      
      if (token && (!expiry || parseInt(expiry) > Date.now())) {
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

// Custom hook to use auth context
function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}

// Export everything at the end
export { AuthContext, AuthProvider, useAuth };