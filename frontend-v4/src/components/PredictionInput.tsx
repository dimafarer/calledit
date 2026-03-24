import { useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { connectAndStream, StreamEvent } from '../services/agentCoreWebSocket';

const PredictionInput = () => {
  const [prompt, setPrompt] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamText, setStreamText] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [predictionId, setPredictionId] = useState<string | null>(null);
  const { getToken } = useAuth();

  const handleSubmit = async () => {
    if (!prompt.trim()) return;

    setIsStreaming(true);
    setError(null);
    setStreamText('');
    setPredictionId(null);

    try {
      const token = getToken();
      if (!token) { setError('Not authenticated'); setIsStreaming(false); return; }

      // Use access token for AgentCore WebSocket JWT auth (not id token)
      const accessToken = localStorage.getItem('accessToken');
      if (!accessToken) { setError('No access token available'); setIsStreaming(false); return; }

      const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone;

      // Decision 121: Connect directly with JWT, no presigned URL needed
      connectAndStream(accessToken, { prediction_text: prompt, timezone }, {
        onEvent: (event: StreamEvent) => {
          switch (event.type) {
            case 'flow_started':
              setPredictionId(event.prediction_id);
              setStreamText('Processing your prediction...\n');
              break;
            case 'text':
              setStreamText(prev => prev + ((event.data?.content as string) || ''));
              break;
            case 'turn_complete':
              setStreamText(prev => prev + '\n---\n');
              break;
            case 'flow_complete':
              setIsStreaming(false);
              break;
            case 'error':
              setError((event.data?.message as string) || 'Agent error');
              setIsStreaming(false);
              break;
          }
        },
        onError: (err) => { setError(err); setIsStreaming(false); },
        onClose: () => { setIsStreaming(false); },
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to connect');
      setIsStreaming(false);
    }
  };

  return (
    <div className="make-predictions-container">
      <div className="input-container">
        <textarea
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder="Enter your prediction..."
          rows={4}
          className="text-box"
          aria-label="Prediction input"
          disabled={isStreaming}
        />
      </div>
      <div className="button-container">
        <button onClick={handleSubmit} disabled={isStreaming || !prompt.trim()} className="send-button" aria-busy={isStreaming}>
          {isStreaming ? 'Streaming...' : 'Make Prediction'}
        </button>
      </div>

      {error && <div className="error-message">{error}</div>}

      {streamText && (
        <div className="streaming-response">
          {predictionId && <p><strong>Prediction:</strong> {predictionId}</p>}
          <pre style={{ whiteSpace: 'pre-wrap', fontFamily: 'inherit' }}>{streamText}</pre>
          {isStreaming && (
            <div className="processing-indicator">
              <span>Streaming</span>
              <span className="processing-dots"><span></span><span></span><span></span></span>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default PredictionInput;
