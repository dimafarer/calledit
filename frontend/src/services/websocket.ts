/**
 * WebSocket Service for CalledIt
 * 
 * Provides WebSocket connection management and message handling
 * for real-time communication with the backend.
 */

export class WebSocketService {
  private socket: WebSocket | null = null;
  private connectionPromise: Promise<void> | null = null;
  private resolveConnection: (() => void) | null = null;
  private rejectConnection: ((error: Error) => void) | null = null;
  private messageHandlers: Map<string, (data: any) => void> = new Map();

  constructor(private url: string) {}

  /**
   * Connect to the WebSocket server
   */
  async connect(): Promise<void> {
    // Return existing connection if already connected
    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
      return Promise.resolve();
    }

    // Return existing connection promise if connection is in progress
    if (this.connectionPromise) {
      return this.connectionPromise;
    }

    // Create new connection promise
    this.connectionPromise = new Promise<void>((resolve, reject) => {
      this.resolveConnection = resolve;
      this.rejectConnection = reject;

      try {
        this.socket = new WebSocket(this.url);

        this.socket.onopen = () => {
          console.log('WebSocket connection established');
          if (this.resolveConnection) {
            this.resolveConnection();
          }
        };

        this.socket.onclose = () => {
          console.log('WebSocket connection closed');
          this.cleanup();
        };

        this.socket.onerror = () => {
          const error = new Error('Failed to connect to WebSocket server');
          if (this.rejectConnection) {
            this.rejectConnection(error);
          }
        };

        this.socket.onmessage = (event) => {
          this.handleMessage(event.data);
        };

      } catch (error) {
        if (this.rejectConnection) {
          this.rejectConnection(error as Error);
        }
      }
    });

    return this.connectionPromise;
  }

  /**
   * Disconnect from the WebSocket server
   */
  disconnect(): void {
    if (this.socket) {
      this.socket.close();
    }
    this.cleanup();
  }

  /**
   * Send a message to the WebSocket server
   */
  async send(action: string, data: any): Promise<void> {
    // Ensure connection is established
    if (!this.socket || this.socket.readyState !== WebSocket.OPEN) {
      if (!this.connectionPromise) {
        throw new Error('WebSocket is not connected');
      }
      await this.connectionPromise;
    }

    if (!this.socket || this.socket.readyState !== WebSocket.OPEN) {
      throw new Error('WebSocket is not connected');
    }

    const message = {
      action,
      ...data
    };

    this.socket.send(JSON.stringify(message));
  }

  /**
   * Register a message handler for a specific message type
   */
  onMessage(type: string, handler: (data: any) => void): void {
    this.messageHandlers.set(type, handler);
  }

  /**
   * Remove a message handler for a specific message type
   */
  offMessage(type: string): void {
    this.messageHandlers.delete(type);
  }

  /**
   * Handle incoming WebSocket messages
   */
  private handleMessage(data: string): void {
    try {
      const message = JSON.parse(data);
      const messageType = message.type;

      if (this.messageHandlers.has(messageType)) {
        const handler = this.messageHandlers.get(messageType);
        if (handler) {
          handler(message);
        }
      } else {
        console.log(`No handler for message type: ${messageType}`, message);
      }
    } catch (error) {
      console.error('Error parsing WebSocket message:', error);
    }
  }

  /**
   * Clean up resources
   */
  private cleanup(): void {
    this.socket = null;
    this.connectionPromise = null;
    this.resolveConnection = null;
    this.rejectConnection = null;
  }
}