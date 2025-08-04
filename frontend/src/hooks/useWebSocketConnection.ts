import { useRef, useCallback, useEffect, useState } from 'react';
import { CallService } from '../services/callService';

interface WebSocketConnectionOptions {
  url: string;
  reconnectAttempts?: number;
  reconnectDelay?: number;
}

export const useWebSocketConnection = (options: WebSocketConnectionOptions) => {
  const { url, reconnectAttempts = 3, reconnectDelay = 1000 } = options;
  const callServiceRef = useRef<CallService | null>(null);
  const reconnectCountRef = useRef(0);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const [callService, setCallService] = useState<CallService | null>(null);
  const [reconnectCount, setReconnectCount] = useState(0);

  const cleanup = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    
    if (callServiceRef.current) {
      callServiceRef.current.cleanup();
      callServiceRef.current = null;
    }
    setCallService(null);
  }, []);

  const initializeConnection = useCallback(() => {
    if (callServiceRef.current) {
      callServiceRef.current.cleanup();
    }
    
    callServiceRef.current = new CallService(url);
    setCallService(callServiceRef.current);
    reconnectCountRef.current = 0;
    setReconnectCount(0);
  }, [url]);

  const handleConnectionError = useCallback((error: string) => {
    console.error('WebSocket connection error:', error);
    
    if (reconnectCountRef.current < reconnectAttempts) {
      reconnectCountRef.current++;
      setReconnectCount(reconnectCountRef.current);
      console.log(`Attempting reconnection ${reconnectCountRef.current}/${reconnectAttempts}`);
      
      reconnectTimeoutRef.current = setTimeout(() => {
        initializeConnection();
      }, reconnectDelay * reconnectCountRef.current);
    }
  }, [reconnectAttempts, reconnectDelay, initializeConnection]);

  useEffect(() => {
    initializeConnection();
    return cleanup;
  }, [initializeConnection, cleanup]);

  return {
    callService,
    handleConnectionError,
    reconnectCount,
    maxReconnectAttempts: reconnectAttempts
  };
};