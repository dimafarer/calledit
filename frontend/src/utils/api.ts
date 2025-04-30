import { useAuth } from '../contexts/AuthContext';

// Base URL for your API Gateway
const API_BASE_URL = import.meta.env.VITE_APIGATEWAY || 'your-api-gateway-url';

export const useApi = () => {
  const { getToken, logout } = useAuth();

  const callApi = async (
    endpoint: string, 
    options: RequestInit = {}
  ) => {
    const token = getToken();
    
    if (!token) {
      throw new Error('No authentication token available');
    }

    const headers = {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
      ...options.headers,
    };

    try {
      const response = await fetch(`${API_BASE_URL}${endpoint}`, {
        ...options,
        headers,
      });

      if (response.status === 401) {
        // Token expired or invalid
        logout();
        throw new Error('Authentication expired');
      }

      if (!response.ok) {
        throw new Error(`API call failed: ${response.statusText}`);
      }

      return await response.json();
    } catch (error) {
      console.error('API call error:', error);
      throw error;
    }
  };

  return { callApi };
};
