import axios, { AxiosRequestConfig } from 'axios';
import { getAccessToken } from './authService';

// Create an axios instance with a base URL
const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '',
});

// Add a request interceptor to add the authorization header
api.interceptors.request.use(
  (config) => {
    const token = getAccessToken();
    
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    
    return config;
  },
  (error) => {
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
    const response = await api({
      method,
      url,
      data,
      ...options,
    });
    
    return response.data;
  } catch (error) {
    console.error(`API ${method} request failed:`, error);
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