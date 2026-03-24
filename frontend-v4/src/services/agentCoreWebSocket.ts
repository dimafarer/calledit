/**
 * AgentCore WebSocket Service — v4 JWT auth → direct WebSocket
 *
 * Decision 121: Browser connects directly to AgentCore Runtime using
 * Cognito JWT via Sec-WebSocket-Protocol header (base64url-encoded).
 * No presigned URL Lambda needed for the WebSocket path.
 */

const V4_API_URL = import.meta.env.VITE_V4_API_URL;
const AGENT_RUNTIME_ARN = import.meta.env.VITE_AGENT_RUNTIME_ARN;
const AGENT_WS_REGION = import.meta.env.VITE_AWS_REGION || 'us-west-2';

export interface StreamEvent {
  type: 'flow_started' | 'text' | 'turn_complete' | 'flow_complete' | 'error';
  prediction_id: string;
  data: Record<string, unknown>;
}

export interface StreamCallbacks {
  onEvent: (event: StreamEvent) => void;
  onError: (error: string) => void;
  onClose: () => void;
}

/** Base64url encode a string (no padding, URL-safe) */
function base64urlEncode(str: string): string {
  return btoa(str)
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=/g, '');
}

/** Build the AgentCore WebSocket URL */
function buildWsUrl(): string {
  const encodedArn = encodeURIComponent(AGENT_RUNTIME_ARN);
  return `wss://bedrock-agentcore.${AGENT_WS_REGION}.amazonaws.com/runtimes/${encodedArn}/ws`;
}

/** Open WebSocket to AgentCore with JWT auth, send prediction, stream events back */
export function connectAndStream(
  token: string,
  payload: { prediction_text: string; user_id?: string; timezone?: string },
  callbacks: StreamCallbacks,
): WebSocket {
  const wssUrl = buildWsUrl();
  const base64Token = base64urlEncode(token);

  // AgentCore accepts JWT via Sec-WebSocket-Protocol header (Decision 121)
  const ws = new WebSocket(wssUrl, [
    `base64UrlBearerAuthorization.${base64Token}`,
    'base64UrlBearerAuthorization',
  ]);

  ws.onopen = () => {
    ws.send(JSON.stringify(payload));
  };

  ws.onmessage = (event) => {
    try {
      const parsed = JSON.parse(event.data);
      if (parsed && parsed.type) {
        callbacks.onEvent(parsed as StreamEvent);
      }
    } catch {
      console.warn('Failed to parse WebSocket message:', String(event.data).slice(0, 100));
    }
  };

  ws.onerror = () => {
    callbacks.onError('WebSocket connection error');
  };

  ws.onclose = () => {
    callbacks.onClose();
  };

  return ws;
}

/** Fetch user's predictions from GET /predictions */
export async function fetchPredictions(token: string) {
  const response = await fetch(`${V4_API_URL}/predictions`, {
    headers: { 'Authorization': `Bearer ${token}` },
  });

  if (!response.ok) {
    const body = await response.text();
    throw new Error(`Predictions request failed (${response.status}): ${body}`);
  }

  const data = await response.json();
  return data.results || [];
}
