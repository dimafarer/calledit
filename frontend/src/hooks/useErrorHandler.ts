import { useState, useCallback } from 'react';

interface ErrorState {
  message: string | null;
  type: 'websocket' | 'improvement' | 'general' | null;
  timestamp: number | null;
}

export const useErrorHandler = () => {
  const [error, setError] = useState<ErrorState>({
    message: null,
    type: null,
    timestamp: null
  });

  const setWebSocketError = useCallback((message: string) => {
    console.error('🔴 WebSocket Error:', message);
    setError({
      message: `WebSocket Error: ${message}`,
      type: 'websocket',
      timestamp: Date.now()
    });
  }, []);

  const setImprovementError = useCallback((message: string) => {
    console.error('🔴 Improvement Error:', message);
    setError({
      message: `Improvement Error: ${message}`,
      type: 'improvement',
      timestamp: Date.now()
    });
  }, []);

  const setGeneralError = useCallback((message: string) => {
    console.error('🔴 General Error:', message);
    setError({
      message,
      type: 'general',
      timestamp: Date.now()
    });
  }, []);

  const clearError = useCallback(() => {
    console.log('✅ Error cleared');
    setError({
      message: null,
      type: null,
      timestamp: null
    });
  }, []);

  const hasError = error.message !== null;

  return {
    error,
    hasError,
    setWebSocketError,
    setImprovementError,
    setGeneralError,
    clearError
  };
};