import { WebSocketService } from './websocket';

export class CallService {
  private webSocketService: WebSocketService;

  constructor(webSocketUrl: string) {
    this.webSocketService = new WebSocketService(webSocketUrl);
  }

  // Make a call with streaming response
  async makeCallWithStreaming(
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

      // Connect and send the call request with timezone
      await this.webSocketService.connect();
      
      // Detect timezone with error handling
      let timezone: string;
      try {
        timezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
        if (!timezone) {
          throw new Error('Timezone detection returned empty value');
        }
      } catch (error) {
        const errorMsg = 'Failed to detect your timezone. Please refresh the page and try again.';
        onError(errorMsg);
        return;
      }
      
      await this.webSocketService.send('makecall', { prompt, timezone });
    } catch (error) {
      onError((error as Error).message);
    }
  }

  // Clean up resources
  cleanup(): void {
    this.webSocketService.disconnect();
  }
}