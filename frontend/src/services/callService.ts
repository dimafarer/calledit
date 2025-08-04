import { WebSocketService } from './websocket';

export class CallService {
  private webSocketService: WebSocketService;
  private onReviewStatus?: (status: string) => void;
  private onReviewComplete?: (data: any) => void;
  private onImprovedResponse?: (data: any) => void;
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
    this.onImprovedResponse = onImprovedResponse;
    
    // Register all handlers BEFORE connecting
      this.webSocketService.onMessage('text', (data) => {
        onTextChunk(data.content);
      });

      this.webSocketService.onMessage('tool', (data) => {
        onToolUse(data.name);
      });

      this.webSocketService.onMessage('call_response', (data) => {
        console.log('✅ CallService: Received call_response:', data);
        // Check if this is an improved response (after improvement workflow)
        if (data.improved || this.isImprovementInProgress) {
          console.log('🔄 CallService: Handling as improved response');
          if (this.onImprovedResponse) {
            this.onImprovedResponse(data.content);
            this.isImprovementInProgress = false; // Reset flag after handling
          }
        } else {
          console.log('📝 CallService: Handling as initial response');
          onComplete(data.content);
        }
      });

      this.webSocketService.onMessage('review_complete', (data) => {
        console.log('✅ CallService: Review completed:', data.data);
        // Pass review data to a callback if provided
        if (this.onReviewComplete) {
          console.log('📋 CallService: Calling onReviewComplete callback');
          this.onReviewComplete(data.data);
        } else {
          console.log('⚠️ CallService: No onReviewComplete callback registered');
        }
      });

      this.webSocketService.onMessage('improvement_questions', (data) => {
        console.log('❓ CallService: Improvement questions received:', data);
        // Handle improvement questions if needed
      });

      this.webSocketService.onMessage('improved_response', (data) => {
        console.log('✨ CallService: Improved response received:', data);
        if (this.onImprovedResponse) {
          this.onImprovedResponse(data.data);
          this.isImprovementInProgress = false;
        }
      });

      this.webSocketService.onMessage('complete', (data) => {
        console.log('🏁 CallService: Process complete:', data);
        // Handle completion status if needed
      });

      this.webSocketService.onMessage('status', (data) => {
        console.log('📊 CallService: Status update:', data);
        if (data.status === 'reviewing' && this.onReviewStatus) {
          this.onReviewStatus('🔍 Reviewing response for improvements...');
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

    try {
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