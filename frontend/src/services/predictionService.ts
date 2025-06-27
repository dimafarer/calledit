import { WebSocketService } from './websocket';

export class PredictionService {
  private webSocketService: WebSocketService;

  constructor(webSocketUrl: string) {
    this.webSocketService = new WebSocketService(webSocketUrl);
  }

  // Make a prediction with streaming response
  async makePredictionWithStreaming(
    prompt: string,
    onTextChunk: (text: string) => void,
    onToolUse: (toolName: string) => void,
    onComplete: (finalResponse: any) => void,
    onError: (error: string) => void
  ): Promise<void> {
    try {
      // Register handlers for different message types
      this.webSocketService.onMessage('text', (data) => {
        onTextChunk(data.content);
      });

      this.webSocketService.onMessage('tool', (data) => {
        onToolUse(data.name);
      });

      this.webSocketService.onMessage('complete', (data) => {
        onComplete(data.content);
      });

      this.webSocketService.onMessage('error', (data) => {
        onError(data.message);
      });

      this.webSocketService.onMessage('status', (data) => {
        if (data.status === 'processing') {
          onTextChunk(data.message + '\n');
        }
      });

      // Connect and send the prediction request
      await this.webSocketService.connect();
      await this.webSocketService.send('makecall', { prompt });
    } catch (error) {
      onError((error as Error).message);
    }
  }

  // Clean up resources
  cleanup(): void {
    this.webSocketService.disconnect();
  }
}