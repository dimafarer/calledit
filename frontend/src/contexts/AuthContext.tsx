import { createContext, useContext, useEffect, useState, useRef } from 'react';

interface AuthContextType {
  isAuthenticated: boolean;
  login: () => void;
  logout: () => void;
  getToken: () => string | null;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  // Add this ref to track if we've already processed the code
  const codeProcessed = useRef(false);
  // Get these values from your Cognito setup
  const REGION = import.meta.env.VITE_AWS_REGION; // Your region
  const CLIENT_ID = import.meta.env.VITE_COGNITO_CLIENT_ID;
  const DOMAIN_PREFIX = import.meta.env.VITE_COGNITO_DOMAIN_PREFIX; 
  let REDIRECT_URI: string; 
  if (import.meta.env.DEV) {
    console.log('Development mode');
    REDIRECT_URI = import.meta.env.VITE_COGNITO_DEV_REDIRECT_URI;
  } else {
    console.log('Production mode');
    REDIRECT_URI = import.meta.env.VITE_COGNITO_PROD_REDIRECT_URI;
  }

  const login = () => {
    const cognitoDomain = `https://${DOMAIN_PREFIX}.auth.${REGION}.amazoncognito.com`;
    const queryParams = new URLSearchParams({
      client_id: CLIENT_ID,
      response_type: 'code',
      scope: 'email openid profile',
      redirect_uri: REDIRECT_URI,
    });
    window.location.href = `${cognitoDomain}/login?${queryParams.toString()}`;
  };

  const logout = () => {
    localStorage.removeItem('idToken');
    localStorage.removeItem('accessToken');
    localStorage.removeItem('refreshToken');
    setIsAuthenticated(false);
  };

  const getToken = () => {
    return localStorage.getItem('idToken');
  };

  useEffect(() => {
    const urlParams = new URLSearchParams(window.location.search);
    const authCode = urlParams.get('code');
    if (authCode && !codeProcessed.current) {
      // console.log('Received auth code:', authCode);
      codeProcessed.current = true;
      console.log('Starting token exchange process');
      const tokenEndpoint = `https://${DOMAIN_PREFIX}.auth.${REGION}.amazoncognito.com/oauth2/token`;
      // Log the exact redirect URI we're using
      console.log('Using redirect URI:', REDIRECT_URI);      
      // Make sure this matches exactly what's configured in Cognito
      const params = new URLSearchParams();
      params.append('grant_type', 'authorization_code');
      params.append('client_id', CLIENT_ID);
      params.append('code', authCode);
      params.append('redirect_uri', REDIRECT_URI);

      console.log('Token request payload:', {
        endpoint: tokenEndpoint,
        parameters: params.toString()
      });

      fetch(tokenEndpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: params.toString(),
      })
      .then(async response => {
        const text = await response.text();
        console.log('Token exchange response:', {
          status: response.status,
          body: text
        });
        if (!response.ok) {
          throw new Error(`Token exchange failed: ${text}`);
        }
        return JSON.parse(text);
      })
      .then(data => {
        console.log('Token exchange successful');
        localStorage.setItem('idToken', data.id_token);
        localStorage.setItem('accessToken', data.access_token);
        localStorage.setItem('refreshToken', data.refresh_token);
        setIsAuthenticated(true);
        
        // Clean up the URL
        window.history.replaceState({}, document.title, window.location.pathname);
      })
      .catch(error => {
        console.error('Authentication error:', error);
      });
    } else {
      // Check if we have a stored token
      const token = localStorage.getItem('idToken');
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
