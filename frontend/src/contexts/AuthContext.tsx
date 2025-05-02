import { createContext, useContext, useEffect, useState, useRef } from 'react';

interface AuthContextType {
  isAuthenticated: boolean;
  login: () => void;
  logout: () => void;
  getToken: () => string | null;
}

// Token storage keys
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

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const codeProcessed = useRef(false);
  
  // Cognito domain URL
  const cognitoDomain = `https://${ENV.DOMAIN_PREFIX}.auth.${ENV.REGION}.amazoncognito.com`;

  const login = () => {
    const queryParams = new URLSearchParams({
      client_id: ENV.CLIENT_ID,
      response_type: 'code',
      scope: 'email openid profile',
      redirect_uri: ENV.REDIRECT_URI,
    });
    window.location.href = `${cognitoDomain}/login?${queryParams.toString()}`;
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

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}