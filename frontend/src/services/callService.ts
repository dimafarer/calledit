import { WebSocketService } from './websocket';

export class CallService {
  private webSocketService: WebSocketService;
  private onReviewStatus?: (status: string) => void;
  private onReviewComplete?: (data: any) => void;
  private isImprovementInProgress: boolean = false;

  constructor(webSocketUrl: string) {
    this.webSocketService = new WebSocketService(webSocketUrl);
  }

  // Make a call with streaming response
  async makeCallWithStreaming(
    prompt: string,
    onTextChunk: (text: string) => void,
    onToolUse: (toolName: string) => void,
    onComplete: (finalResponse: any) => void,
    onError: (error: string) => void,
    onReviewStatus?: (status: string) => void,
    onReviewComplete?: (data: any) => void,
    onImprovedResponse?: (data: any) => void
  ): Promise<void> {
    this.onReviewStatus = onReviewStatus;
    this.onReviewComplete = onReviewComplete;
    try {
      // Register handlers for different message types
      this.webSocketService.onMessage('text', (data) => {
        onTextChunk(data.content);
      });

      this.webSocketService.onMessage('tool', (data) => {
        onToolUse(data.name);
      });

      this.webSocketService.onMessage('call_response', (data) => {
        console.log('Received call_response:', data);
        // Check if this is an improved response (after improvement workflow)
        if (data.improved || this.isImprovementInProgress) {
          if (onImprovedResponse) {
            onImprovedResponse(data.content);
          }
        } else {
          onComplete(data.content);
        }
      });

      this.webSocketService.onMessage('review_complete', (data) => {
        console.log('Review completed:', data.data);
        // Pass review data to a callback if provided
        if (this.onReviewComplete) {
          this.onReviewComplete(data.data);
        }
      });

      this.webSocketService.onMessage('status', (data) => {
        if (data.status === 'reviewing') {
          if (this.onReviewStatus) {
            this.onReviewStatus('🔍 Reviewing response for improvements...');
          }
        }
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

  // Set improvement in progress flag
  setImprovementInProgress(inProgress: boolean): void {
    this.isImprovementInProgress = inProgress;
  }

  // Get WebSocket service for direct access
  get websocket() {
    return this.webSocketService;
  }

  // Clean up resources
  cleanup(): void {
    this.webSocketService.disconnect();
  }
}