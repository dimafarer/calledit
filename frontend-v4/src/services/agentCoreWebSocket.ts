/**
 * AgentCore WebSocket Service — v4 presigned URL → direct WebSocket
 *
 * Replaces v3's API Gateway WebSocket proxy pattern.
 * Flow: POST /presigned-url → wss:// → SSE stream events
 */

const V4_API_URL = import.meta.env.VITE_V4_API_URL;

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

/** Call POST /presigned-url with Cognito JWT, returns wss:// URL + session_id */
export async function getPresignedUrl(token: string): Promise<{ url: string; session_id: string }> {
  const response = await fetch(`${V4_API_URL}/presigned-url`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    const body = await response.text();
    throw new Error(`Presigned URL request failed (${response.status}): ${body}`);
  }

  return response.json();
}

/** Parse SSE-formatted data from WebSocket message */
export function parseSSEEvents(raw: string): StreamEvent[] {
  const events: StreamEvent[] = [];
  const parts = raw.split('\n\n');

  for (const part of parts) {
    const trimmed = part.trim();
    if (!trimmed) continue;

    // Strip "data: " prefix if present
    const jsonStr = trimmed.startsWith('data: ') ? trimmed.slice(6) : trimmed;

    try {
      const parsed = JSON.parse(jsonStr);
      if (parsed && parsed.type) {
        events.push(parsed as StreamEvent);
      }
    } catch {
      // Skip malformed events, log for debugging
      console.warn('Failed to parse SSE event:', jsonStr.slice(0, 100));
    }
  }

  return events;
}

/** Open WebSocket to presigned URL, send prediction, stream events back */
export function connectAndStream(
  wssUrl: string,
  payload: { prediction_text: string; user_id?: string; timezone?: string },
  callbacks: StreamCallbacks,
): WebSocket {
  const ws = new WebSocket(wssUrl);

  ws.onopen = () => {
    ws.send(JSON.stringify(payload));
  };

  ws.onmessage = (event) => {
    const events = parseSSEEvents(event.data);
    for (const e of events) {
      callbacks.onEvent(e);
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
