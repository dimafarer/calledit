import { createContext, useContext, useEffect, useState } from 'react';

interface AuthContextType {
  isAuthenticated: boolean;
  login: () => void;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  // Get these values from your Cognito setup
  // const REGION = import.meta.env.VITE_AWS_REGION; // Your region
  // const USER_POOL_ID = import.meta.env.VITE_COGNITO_USER_POOL_ID;
  // const CLIENT_ID = import.meta.env.VITE_COGNITO_CLIENT_ID;
  // const REDIRECT_URI = import.meta.env.VITE_COGNITO_REDIRECT_URI; // localhost or your CloudFront URL in prod
  // const DOMAIN_PREFIX = import.meta.env.VITE_COGNITO_DOMAIN_PREFIX; 

  const REGION = 'us-west-2';
  const USER_POOL_ID = 'your-user-pool-id'; // Fill this in
  const CLIENT_ID = '753gn25jle081ajqabpd4lbin9';
  const DOMAIN_PREFIX = 'calledit-backend-894249332178-domain';
  const REDIRECT_URI = process.env.NODE_ENV === 'development' 
    ? 'http://localhost:5173'
    : 'https://d2k653cdpjxjdu.cloudfront.net';

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
    // Clear any local tokens
    localStorage.removeItem('accessToken');
    setIsAuthenticated(false);
  };

  useEffect(() => {
    // Check for authorization code in URL when the app loads
    const urlParams = new URLSearchParams(window.location.search);
    const authCode = urlParams.get('code');

    if (authCode) {
      // Exchange the code for tokens
      fetch('/auth/token', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          code: authCode,
          redirectUri: REDIRECT_URI,
        }),
      })
      .then(response => response.json())
      .then(data => {
        if (data.accessToken) {
          localStorage.setItem('accessToken', data.accessToken);
          setIsAuthenticated(true);
          // Clean up the URL
          window.history.replaceState({}, document.title, window.location.pathname);
        }
      })
      .catch(error => {
        console.error('Authentication error:', error);
      });
    }

    // Check if we have a valid token
    const token = localStorage.getItem('accessToken');
    if (token) {
      setIsAuthenticated(true);
    }
  }, []);

  return (
    <AuthContext.Provider value={{ isAuthenticated, login, logout }}>
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
