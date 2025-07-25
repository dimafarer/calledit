import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { WebSocketService } from './websocket';

// Mock WebSocket
interface MockWebSocket {
  readyState: number;
  onopen: ((event: Event) => void) | null;
  onclose: ((event: CloseEvent) => void) | null;
  onerror: ((event: Event) => void) | null;
  onmessage: ((event: MessageEvent) => void) | null;
  send: (data: string) => void;
  close: () => void;
  simulateMessage: (data: any) => void;
  simulateError: () => void;
}

const createMockWebSocket = (): MockWebSocket => ({
  readyState: WebSocket.CONNECTING,
  onopen: null,
  onclose: null,
  onerror: null,
  onmessage: null,
  send: vi.fn(),
  close: vi.fn(),
  simulateMessage: function(data: any) {
    if (this.onmessage) {
      this.onmessage({ data: JSON.stringify(data) } as MessageEvent);
    }
  },
  simulateError: function() {
    if (this.onerror) {
      this.onerror(new Event('error'));
    }
  }
});

describe('WebSocketService', () => {
  let mockWebSocket: MockWebSocket;
  let webSocketService: WebSocketService;
  const testUrl = 'wss://test-websocket-url';

  beforeEach(() => {
    mockWebSocket = createMockWebSocket();
    
    // Mock the global WebSocket constructor
    global.WebSocket = vi.fn().mockImplementation(() => mockWebSocket) as any;
    
    webSocketService = new WebSocketService(testUrl);
  });

  afterEach(() => {
    vi.resetAllMocks();
  });

  describe('connect', () => {
    it('creates a new WebSocket connection', async () => {
      const connectPromise = webSocketService.connect();
      
      // Simulate successful connection
      mockWebSocket.readyState = WebSocket.OPEN;
      if (mockWebSocket.onopen) {
        mockWebSocket.onopen(new Event('open'));
      }
      
      await connectPromise;
      
      expect(global.WebSocket).toHaveBeenCalledWith(testUrl);
    });

    it('resolves when connection is established', async () => {
      const connectPromise = webSocketService.connect();
      
      // Simulate successful connection
      mockWebSocket.readyState = WebSocket.OPEN;
      if (mockWebSocket.onopen) {
        mockWebSocket.onopen(new Event('open'));
      }
      
      await expect(connectPromise).resolves.toBeUndefined();
    });

    it('rejects when connection fails', async () => {
      const connectPromise = webSocketService.connect();
      
      // Simulate connection error
      if (mockWebSocket.onerror) {
        mockWebSocket.onerror(new Event('error'));
      }
      
      await expect(connectPromise).rejects.toThrow('Failed to connect to WebSocket server');
    });

    it('returns existing connection if already connected', async () => {
      // First connection
      const firstConnectPromise = webSocketService.connect();
      mockWebSocket.readyState = WebSocket.OPEN;
      if (mockWebSocket.onopen) {
        mockWebSocket.onopen(new Event('open'));
      }
      await firstConnectPromise;
      
      // Second connection should return immediately
      const secondConnectPromise = webSocketService.connect();
      await expect(secondConnectPromise).resolves.toBeUndefined();
      
      // WebSocket constructor should only be called once
      expect(global.WebSocket).toHaveBeenCalledTimes(1);
    });

    it('returns existing connection promise if connection is in progress', async () => {
      const firstConnectPromise = webSocketService.connect();
      const secondConnectPromise = webSocketService.connect();
      
      // Both should be the same promise
      expect(firstConnectPromise).toStrictEqual(secondConnectPromise);
      
      // Complete the connection
      mockWebSocket.readyState = WebSocket.OPEN;
      if (mockWebSocket.onopen) {
        mockWebSocket.onopen(new Event('open'));
      }
      
      await Promise.all([firstConnectPromise, secondConnectPromise]);
    });
  });

  describe('disconnect', () => {
    it('closes the WebSocket connection', async () => {
      // First connect to have a socket to close
      const connectPromise = webSocketService.connect();
      mockWebSocket.readyState = WebSocket.OPEN;
      if (mockWebSocket.onopen) {
        mockWebSocket.onopen(new Event('open'));
      }
      await connectPromise;
      
      webSocketService.disconnect();
      
      expect(mockWebSocket.close).toHaveBeenCalled();
    });

    it('handles disconnect when not connected', () => {
      expect(() => webSocketService.disconnect()).not.toThrow();
    });
  });

  describe('send', () => {
    beforeEach(async () => {
      const connectPromise = webSocketService.connect();
      mockWebSocket.readyState = WebSocket.OPEN;
      if (mockWebSocket.onopen) {
        mockWebSocket.onopen(new Event('open'));
      }
      await connectPromise;
    });

    it('sends message when connected', async () => {
      const testAction = 'test-action';
      const testData = { key: 'value' };
      
      await webSocketService.send(testAction, testData);
      
      expect(mockWebSocket.send).toHaveBeenCalledWith(
        JSON.stringify({ action: testAction, ...testData })
      );
    });

    it('throws error when not connected', async () => {
      webSocketService.disconnect();
      
      await expect(
        webSocketService.send('test-action', {})
      ).rejects.toThrow('WebSocket is not connected');
    });

    it('waits for connection if connection is in progress', async () => {
      const newService = new WebSocketService(testUrl);
      const newMockSocket = createMockWebSocket();
      global.WebSocket = vi.fn().mockImplementation(() => newMockSocket) as any;
      
      // Start connection but don't complete it yet
      const connectPromise = newService.connect();
      
      // Try to send while connecting
      const sendPromise = newService.send('test-action', {});
      
      // Complete the connection
      newMockSocket.readyState = WebSocket.OPEN;
      if (newMockSocket.onopen) {
        newMockSocket.onopen(new Event('open'));
      }
      
      await connectPromise;
      await sendPromise;
      
      expect(newMockSocket.send).toHaveBeenCalled();
    });
  });

  describe('message handling', () => {
    beforeEach(async () => {
      const connectPromise = webSocketService.connect();
      mockWebSocket.readyState = WebSocket.OPEN;
      if (mockWebSocket.onopen) {
        mockWebSocket.onopen(new Event('open'));
      }
      await connectPromise;
    });

    it('registers and calls message handlers', () => {
      const handler = vi.fn();
      const testMessage = { type: 'test', content: 'test content' };
      
      webSocketService.onMessage('test', handler);
      mockWebSocket.simulateMessage(testMessage);
      
      expect(handler).toHaveBeenCalledWith(testMessage);
    });

    it('handles multiple message types', () => {
      const textHandler = vi.fn();
      const errorHandler = vi.fn();
      
      webSocketService.onMessage('text', textHandler);
      webSocketService.onMessage('error', errorHandler);
      
      mockWebSocket.simulateMessage({ type: 'text', content: 'hello' });
      mockWebSocket.simulateMessage({ type: 'error', message: 'error occurred' });
      
      expect(textHandler).toHaveBeenCalledWith({ type: 'text', content: 'hello' });
      expect(errorHandler).toHaveBeenCalledWith({ type: 'error', message: 'error occurred' });
    });

    it('removes message handlers', () => {
      const handler = vi.fn();
      
      webSocketService.onMessage('test', handler);
      webSocketService.offMessage('test');
      
      mockWebSocket.simulateMessage({ type: 'test', content: 'test' });
      
      expect(handler).not.toHaveBeenCalled();
    });

    it('handles messages with no registered handler', () => {
      const consoleSpy = vi.spyOn(console, 'log').mockImplementation(() => {});
      
      mockWebSocket.simulateMessage({ type: 'unknown', content: 'test' });
      
      expect(consoleSpy).toHaveBeenCalledWith(
        'No handler for message type: unknown',
        { type: 'unknown', content: 'test' }
      );
      
      consoleSpy.mockRestore();
    });

    it('handles invalid JSON messages', () => {
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
      
      if (mockWebSocket.onmessage) {
        mockWebSocket.onmessage({ data: 'invalid json' } as MessageEvent);
      }
      
      expect(consoleSpy).toHaveBeenCalledWith(
        'Error parsing WebSocket message:',
        expect.any(Error)
      );
      
      consoleSpy.mockRestore();
    });
  });

  describe('connection lifecycle', () => {
    it('cleans up on connection close', async () => {
      const connectPromise = webSocketService.connect();
      mockWebSocket.readyState = WebSocket.OPEN;
      if (mockWebSocket.onopen) {
        mockWebSocket.onopen(new Event('open'));
      }
      await connectPromise;
      
      // Simulate connection close
      if (mockWebSocket.onclose) {
        mockWebSocket.onclose(new CloseEvent('close'));
      }
      
      // Should be able to connect again (creates new WebSocket)
      const newConnectPromise = webSocketService.connect();
      expect(newConnectPromise).toBeDefined();
    });

    it('handles connection errors gracefully', async () => {
      const connectPromise = webSocketService.connect();
      
      // Simulate connection error
      mockWebSocket.simulateError();
      
      await expect(connectPromise).rejects.toThrow();
    });
  });
});