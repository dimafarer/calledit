import axios, { AxiosRequestConfig } from 'axios';
import { getAccessToken } from './authService';

// Create an axios instance with a base URL
// Using VITE_APIGATEWAY for consistency with other components
const api = axios.create({
  baseURL: import.meta.env.VITE_APIGATEWAY || '',
  // Add withCredentials to allow cookies to be sent with cross-origin requests
  withCredentials: true,
});

// Log the API base URL for debugging
console.log('API Service initialized with base URL:', import.meta.env.VITE_APIGATEWAY || 'No API URL defined');

// Add a request interceptor to add the authorization header
api.interceptors.request.use(
  async (config) => {
    try {
      // Properly await the async getAccessToken function
      const token = await getAccessToken();
      
      if (token) {
        console.log('Adding authorization token to request');
        config.headers.Authorization = `Bearer ${token}`;
      } else {
        console.warn('No authorization token available');
      }
    } catch (error) {
      console.error('Error getting access token for request:', error);
    }
    
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Add a response interceptor to handle common errors
api.interceptors.response.use(
  (response) => {
    // Any status code within the range of 2xx causes this function to trigger
    return response;
  },
  (error) => {
    // Any status codes outside the range of 2xx cause this function to trigger
    if (error.response) {
      // The request was made and the server responded with a status code
      // that falls out of the range of 2xx
      console.error(`API Error Response: ${error.response.status}`, '[RESPONSE_DATA_REDACTED]');
      
      // Check for specific error types
      if (error.response.status === 401) {
        console.error('Authentication error: Token might be invalid or expired');
      } else if (error.response.status === 403) {
        console.error('Authorization error: Insufficient permissions');
      }
    } else if (error.request) {
      // The request was made but no response was received
      // This is likely a CORS error
      console.error('No response received. This might be a CORS issue:', error.message?.replace(/[\r\n]/g, '') || 'Unknown error');
      
      // Create a more informative error object
      const corsError = new Error('CORS Error: Unable to access the API. This might be due to cross-origin restrictions.');
      corsError.name = 'CORSError';
      return Promise.reject(corsError);
    }
    
    return Promise.reject(error);
  }
);

// Generic function to make API requests
export const apiRequest = async <T>(
  method: string,
  url: string,
  data?: any,
  options?: AxiosRequestConfig
): Promise<T> => {
  try {
    console.log(`Making ${method} request to ${url.replace(/[\r\n]/g, '')}`);
    const response = await api({
      method,
      url,
      data,
      ...options,
    });
    
    console.log(`Successful ${method} response from ${url.replace(/[\r\n]/g, '')}:`, response.status);
    return response.data;
  } catch (error: any) {
    console.error(`API ${method} request failed:`, error);
    
    // Enhanced error logging for debugging
    if (error.response) {
      // The request was made and the server responded with a status code
      // that falls out of the range of 2xx
      console.error('Response status:', error.response.status);
      console.error('Response headers:', error.response.headers);
      console.error('Response data:', '[REDACTED]');
      
      // Check for specific error types
      if (error.response.status === 401) {
        console.error('Authentication error: Token might be invalid or expired');
      } else if (error.response.status === 403) {
        console.error('Authorization error: Insufficient permissions');
      }
    } else if (error.request) {
      // The request was made but no response was received
      console.error('No response received from server. This might be a CORS or network issue.');
      console.error('Request details:', error.request);
    } else {
      // Something happened in setting up the request that triggered an Error
      console.error('Error setting up request:', error.message);
    }
    
    throw error;
  }
};

// Helper functions for common HTTP methods
export const get = <T>(url: string, options?: AxiosRequestConfig): Promise<T> => {
  return apiRequest<T>('GET', url, undefined, options);
};

export const post = <T>(url: string, data?: any, options?: AxiosRequestConfig): Promise<T> => {
  return apiRequest<T>('POST', url, data, options);
};

export const put = <T>(url: string, data?: any, options?: AxiosRequestConfig): Promise<T> => {
  return apiRequest<T>('PUT', url, data, options);
};

export const del = <T>(url: string, options?: AxiosRequestConfig): Promise<T> => {
  return apiRequest<T>('DELETE', url, undefined, options);
};