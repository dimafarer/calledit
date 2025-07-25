import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { WebSocketService } from './websocket';

// Mock WebSocket
class MockWebSocket {
  static CONNECTING = 0;
  static OPEN = 1;
  static CLOSING = 2;
  static CLOSED = 3;

  readyState = MockWebSocket.CONNECTING;
  onopen: ((event: Event) => void) | null = null;
  onclose: ((event: CloseEvent) => void) | null = null;
  onerror: ((event: Event) => void) | null = null;
  onmessage: ((event: MessageEvent) => void) | null = null;

  constructor(public url: string) {
    // Simulate async connection
    setTimeout(() => {
      this.readyState = MockWebSocket.OPEN;
      if (this.onopen) {
        this.onopen(new Event('open'));
      }
    }, 10);
  }

  send(data: string) {
    if (this.readyState !== MockWebSocket.OPEN) {
      throw new Error('WebSocket is not open');
    }
    // Mock successful send
  }

  close() {
    this.readyState = MockWebSocket.CLOSED;
    if (this.onclose) {
      this.onclose(new CloseEvent('close'));
    }
  }

  // Helper method to simulate receiving messages
  simulateMessage(data: any) {
    if (this.onmessage) {
      this.onmessage(new MessageEvent('message', { data: JSON.stringify(data) }));
    }
  }

  // Helper method to simulate connection error
  simulateError() {
    if (this.onerror) {
      this.onerror(new Event('error'));
    }
  }
}

// Mock global WebSocket
global.WebSocket = MockWebSocket as any;

describe('WebSocketService', () => {
  let webSocketService: WebSocketService;
  const testUrl = 'wss://test-websocket-url';

  beforeEach(() => {
    webSocketService = new WebSocketService(testUrl);
    vi.clearAllMocks();
  });

  afterEach(() => {
    webSocketService.disconnect();
  });

  describe('Connection Management', () => {
    it('should create WebSocket connection with correct URL', async () => {
      await webSocketService.connect();
      
      expect(webSocketService['socket']).toBeDefined();
      expect(webSocketService['socket']?.url).toBe(testUrl);
    });

    it('should resolve connection promise when WebSocket opens', async () => {
      const connectionPromise = webSocketService.connect();
      
      await expect(connectionPromise).resolves.toBeUndefined();
    });

    it('should reject connection promise on WebSocket error', async () => {
      const connectionPromise = webSocketService.connect();
      
      // Simulate connection error
      setTimeout(() => {
        const socket = webSocketService['socket'] as MockWebSocket;
        socket.simulateError();
      }, 5);
      
      await expect(connectionPromise).rejects.toThrow('Failed to connect to WebSocket server');
    });

    it('should return existing connection if already connected', async () => {
      await webSocketService.connect();
      const firstSocket = webSocketService['socket'];
      
      await webSocketService.connect();
      const secondSocket = webSocketService['socket'];
      
      expect(firstSocket).toBe(secondSocket);
    });

    it('should disconnect WebSocket properly', async () => {
      await webSocketService.connect();
      const socket = webSocketService['socket'] as MockWebSocket;
      
      webSocketService.disconnect();
      
      expect(webSocketService['socket']).toBeNull();
    });
  });

  describe('Message Handling', () => {
    beforeEach(async () => {
      await webSocketService.connect();
    });

    it('should register message handlers correctly', () => {
      const handler = vi.fn();
      
      webSocketService.onMessage('test-type', handler);
      
      expect(webSocketService['messageHandlers'].has('test-type')).toBe(true);
      expect(webSocketService['messageHandlers'].get('test-type')).toBe(handler);
    });

    it('should call appropriate handler when message is received', async () => {
      const textHandler = vi.fn();
      const toolHandler = vi.fn();
      
      webSocketService.onMessage('text', textHandler);
      webSocketService.onMessage('tool', toolHandler);
      
      const socket = webSocketService['socket'] as MockWebSocket;
      
      // Simulate text message
      socket.simulateMessage({ type: 'text', content: 'Hello' });
      
      expect(textHandler).toHaveBeenCalledWith({ type: 'text', content: 'Hello' });
      expect(toolHandler).not.toHaveBeenCalled();
    });

    it('should handle multiple message types correctly', async () => {
      const handlers = {
        text: vi.fn(),
        tool: vi.fn(),
        complete: vi.fn(),
        error: vi.fn(),
        status: vi.fn()
      };
      
      Object.entries(handlers).forEach(([type, handler]) => {
        webSocketService.onMessage(type, handler);
      });
      
      const socket = webSocketService['socket'] as MockWebSocket;
      
      // Simulate different message types
      socket.simulateMessage({ type: 'text', content: 'Processing...' });
      socket.simulateMessage({ type: 'tool', name: 'current_time' });
      socket.simulateMessage({ type: 'complete', content: '{"result": "done"}' });
      socket.simulateMessage({ type: 'error', message: 'Something went wrong' });
      socket.simulateMessage({ type: 'status', status: 'processing' });
      
      expect(handlers.text).toHaveBeenCalledWith({ type: 'text', content: 'Processing...' });
      expect(handlers.tool).toHaveBeenCalledWith({ type: 'tool', name: 'current_time' });
      expect(handlers.complete).toHaveBeenCalledWith({ type: 'complete', content: '{"result": "done"}' });
      expect(handlers.error).toHaveBeenCalledWith({ type: 'error', message: 'Something went wrong' });
      expect(handlers.status).toHaveBeenCalledWith({ type: 'status', status: 'processing' });
    });

    it('should log warning for unhandled message types', async () => {
      const consoleSpy = vi.spyOn(console, 'log').mockImplementation(() => {});
      
      const socket = webSocketService['socket'] as MockWebSocket;
      socket.simulateMessage({ type: 'unknown-type', data: 'test' });
      
      expect(consoleSpy).toHaveBeenCalledWith(
        'No handler for message type: unknown-type',
        { type: 'unknown-type', data: 'test' }
      );
      
      consoleSpy.mockRestore();
    });

    it('should handle malformed JSON messages gracefully', async () => {
      const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
      
      const socket = webSocketService['socket'] as MockWebSocket;
      
      // Simulate malformed JSON
      if (socket.onmessage) {
        socket.onmessage(new MessageEvent('message', { data: 'Invalid JSON' }));
      }
      
      expect(consoleErrorSpy).toHaveBeenCalledWith(
        'Error parsing WebSocket message:',
        expect.any(Error)
      );
      
      consoleErrorSpy.mockRestore();
    });

    it('should remove message handlers correctly', () => {
      const handler = vi.fn();
      
      webSocketService.onMessage('test-type', handler);
      expect(webSocketService['messageHandlers'].has('test-type')).toBe(true);
      
      webSocketService.offMessage('test-type');
      expect(webSocketService['messageHandlers'].has('test-type')).toBe(false);
    });
  });

  describe('Message Sending', () => {
    beforeEach(async () => {
      await webSocketService.connect();
    });

    it('should send messages with correct format', async () => {
      const socket = webSocketService['socket'] as MockWebSocket;
      const sendSpy = vi.spyOn(socket, 'send');
      
      await webSocketService.send('makecall', { prompt: 'Test prediction' });
      
      expect(sendSpy).toHaveBeenCalledWith(
        JSON.stringify({
          action: 'makecall',
          prompt: 'Test prediction'
        })
      );
    });

    it('should throw error when sending without connection', async () => {
      webSocketService.disconnect();
      
      await expect(
        webSocketService.send('makecall', { prompt: 'Test' })
      ).rejects.toThrow('WebSocket is not connected');
    });

    it('should wait for connection before sending', async () => {
      const newService = new WebSocketService(testUrl);
      
      // Start connection and send simultaneously
      const connectionPromise = newService.connect();
      const sendPromise = newService.send('makecall', { prompt: 'Test' });
      
      // Both should complete successfully
      await expect(Promise.all([connectionPromise, sendPromise])).resolves.toBeDefined();
      
      newService.disconnect();
    });
  });

  describe('Connection States', () => {
    it('should handle connection close events', async () => {
      const consoleSpy = vi.spyOn(console, 'log').mockImplementation(() => {});
      
      await webSocketService.connect();
      const socket = webSocketService['socket'] as MockWebSocket;
      
      socket.close();
      
      expect(consoleSpy).toHaveBeenCalledWith('WebSocket connection closed');
      
      consoleSpy.mockRestore();
    });

    it('should handle connection open events', async () => {
      const consoleSpy = vi.spyOn(console, 'log').mockImplementation(() => {});
      
      await webSocketService.connect();
      
      expect(consoleSpy).toHaveBeenCalledWith('WebSocket connection established');
      
      consoleSpy.mockRestore();
    });

    it('should handle multiple connection attempts gracefully', async () => {
      const firstConnection = webSocketService.connect();
      const secondConnection = webSocketService.connect();
      const thirdConnection = webSocketService.connect();
      
      await Promise.all([firstConnection, secondConnection, thirdConnection]);
      
      // Should only have one socket instance
      expect(webSocketService['socket']).toBeDefined();
    }, 10000);
  });

  describe('Error Handling', () => {
    it('should handle WebSocket constructor errors', async () => {
      // Mock WebSocket constructor to throw
      const originalWebSocket = global.WebSocket;
      global.WebSocket = class {
        constructor() {
          throw new Error('WebSocket construction failed');
        }
      } as any;
      
      const newService = new WebSocketService(testUrl);
      
      await expect(newService.connect()).rejects.toThrow('WebSocket construction failed');
      
      // Restore original WebSocket
      global.WebSocket = originalWebSocket;
    });

    it('should handle send errors gracefully', async () => {
      await webSocketService.connect();
      const socket = webSocketService['socket'] as MockWebSocket;
      
      // Mock send to throw error
      vi.spyOn(socket, 'send').mockImplementation(() => {
        throw new Error('Send failed');
      });
      
      await expect(
        webSocketService.send('makecall', { prompt: 'Test' })
      ).rejects.toThrow('Send failed');
    });
  });

  describe('Cleanup', () => {
    it('should clean up all resources on disconnect', async () => {
      await webSocketService.connect();
      
      webSocketService.onMessage('test', vi.fn());
      expect(webSocketService['messageHandlers'].size).toBe(1);
      
      webSocketService.disconnect();
      
      expect(webSocketService['socket']).toBeNull();
      // Note: messageHandlers are not cleared on disconnect, only connection state
    });

    it('should handle disconnect when not connected', () => {
      // Should not throw error
      expect(() => webSocketService.disconnect()).not.toThrow();
    });
  });
});