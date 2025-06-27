// WebSocket service for handling streaming predictions
export class WebSocketService {
  private socket: WebSocket | null = null;
  private messageHandlers: Map<string, (data: any) => void> = new Map();
  private connectionPromise: Promise<void> | null = null;
  private resolveConnection: (() => void) | null = null;
  private rejectConnection: ((error: Error) => void) | null = null;

  constructor(private url: string) {}

  // Connect to the WebSocket server
  connect(): Promise<void> {
    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
      return Promise.resolve();
    }

    this.connectionPromise = new Promise((resolve, reject) => {
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
        };

        this.socket.onerror = (error) => {
          console.error('WebSocket error:', error);
          if (this.rejectConnection) {
            this.rejectConnection(new Error('Failed to connect to WebSocket server'));
          }
        };

        this.socket.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            const type = data.type;

            if (this.messageHandlers.has(type)) {
              this.messageHandlers.get(type)!(data);
            } else {
              console.log(`No handler for message type: ${type}`, data);
            }
          } catch (error) {
            console.error('Error parsing WebSocket message:', error);
          }
        };
      } catch (error) {
        if (this.rejectConnection) {
          this.rejectConnection(error as Error);
        }
      }
    });

    return this.connectionPromise;
  }

  // Disconnect from the WebSocket server
  disconnect(): void {
    if (this.socket) {
      this.socket.close();
      this.socket = null;
    }
  }

  // Send a message to the WebSocket server
  async send(action: string, data: any): Promise<void> {
    await this.connect();

    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
      const message = JSON.stringify({
        action,
        ...data,
      });
      this.socket.send(message);
    } else {
      throw new Error('WebSocket is not connected');
    }
  }

  // Register a handler for a specific message type
  onMessage(type: string, handler: (data: any) => void): void {
    this.messageHandlers.set(type, handler);
  }

  // Remove a handler for a specific message type
  offMessage(type: string): void {
    this.messageHandlers.delete(type);
  }
}