/**
 * CallService — v2 Unified Graph Protocol
 *
 * Handles WebSocket communication with the prediction pipeline backend.
 *
 * v2 CHANGES:
 * - prediction_ready replaces call_response (pipeline results, immediately submittable)
 * - review_ready replaces review_complete (improvement suggestions from ReviewAgent)
 * - sendClarification() enables multi-round refinement (clarify action)
 * - Removed: call_response, review_complete, improvement_questions, improved_response handlers
 * - Removed: isImprovementInProgress flag (v1 HITL artifact)
 *
 * MESSAGE FLOW:
 * Round 1 (makecall):
 *   Client → {action: "makecall", prompt, timezone}
 *   Server → {type: "status", status: "processing"}
 *   Server → {type: "prediction_ready", data: {...}}  ← user can submit now
 *   Server → {type: "review_ready", data: {...}}       ← improvement suggestions
 *   Server → {type: "complete", status: "ready"}
 *
 * Round 2+ (clarify):
 *   Client → {action: "clarify", user_input, current_state}
 *   Server → same flow as above with updated results
 */

import { WebSocketService } from './websocket';

export class CallService {
  private webSocketService: WebSocketService;
  private onReviewComplete?: (data: any) => void;

  constructor(webSocketUrl: string) {
    this.webSocketService = new WebSocketService(webSocketUrl);
  }

  /**
   * Make a prediction call with streaming response (round 1).
   *
   * Registers WebSocket message handlers and sends the makecall action.
   * The backend responds with prediction_ready (pipeline results) and
   * review_ready (improvement suggestions) as separate messages.
   */
  async makeCallWithStreaming(
    prompt: string,
    onTextChunk: (text: string) => void,
    onToolUse: (toolName: string) => void,
    onComplete: (finalResponse: any) => void,
    onError: (error: string) => void,
    onReviewComplete?: (data: any) => void
  ): Promise<void> {
    this.onReviewComplete = onReviewComplete;

    // Register all handlers BEFORE connecting

    // Agent text streaming — real-time text generation from agents
    this.webSocketService.onMessage('text', (data) => {
      onTextChunk(data.content);
    });

    // Agent tool usage — shows which tools agents are calling
    this.webSocketService.onMessage('tool', (data) => {
      onToolUse(data.name);
    });

    // v2: prediction_ready — pipeline complete, user can submit immediately.
    // This replaces the v1 call_response handler. The data contains the
    // structured prediction with all agent outputs + metadata.
    this.webSocketService.onMessage('prediction_ready', (data) => {
      console.log('✅ CallService: Received prediction_ready:', data);
      onComplete(data.data);
    });

    // v2: review_ready — ReviewAgent meta-analysis complete.
    // This replaces the v1 review_complete handler. Contains reviewable
    // sections with improvement questions. Arrives AFTER prediction_ready.
    this.webSocketService.onMessage('review_ready', (data) => {
      console.log('✅ CallService: Review ready:', data);
      if (this.onReviewComplete) {
        this.onReviewComplete(data.data);
      }
    });

    // Graph execution complete — no more messages for this round.
    this.webSocketService.onMessage('complete', (data) => {
      console.log('🏁 CallService: Round complete:', data);
    });

    // Status updates — processing indicator for the UI.
    this.webSocketService.onMessage('status', (data) => {
      console.log('📊 CallService: Status:', data);
      if (data.status === 'processing' && data.message) {
        onTextChunk(data.message + '\n');
      }
    });

    // Error messages from the backend.
    this.webSocketService.onMessage('error', (data) => {
      onError(data.message);
    });

    try {
      await this.webSocketService.connect();

      // Detect timezone with error handling
      let timezone: string;
      try {
        timezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
        if (!timezone) {
          throw new Error('Timezone detection returned empty value');
        }
      } catch (error) {
        onError('Failed to detect your timezone. Please refresh the page and try again.');
        return;
      }

      await this.webSocketService.send('makecall', { prompt, timezone });
    } catch (error) {
      onError((error as Error).message);
    }
  }

  /**
   * Send a clarification to refine the prediction (round 2+).
   *
   * The frontend sends the user's clarification text plus the complete
   * current state (from the most recent prediction_ready). The backend
   * re-runs the full graph with enriched state — agents see their
   * previous output and decide whether to confirm or update.
   *
   * The same prediction_ready + review_ready flow fires again with
   * updated results.
   */
  async sendClarification(userInput: string, currentState: any): Promise<void> {
    await this.webSocketService.send('clarify', {
      user_input: userInput,
      current_state: currentState,
    });
  }

  /** Get WebSocket service for direct access */
  get websocket() {
    return this.webSocketService;
  }

  /** Clean up resources */
  cleanup(): void {
    this.webSocketService.disconnect();
  }
}
