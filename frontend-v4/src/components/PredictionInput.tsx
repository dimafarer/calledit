import { useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { connectAndStream, StreamEvent } from '../services/agentCoreWebSocket';

interface ReviewSection {
  section: string;
  improvable: boolean;
  questions: string[];
  reasoning: string;
}

interface PredictionBundle {
  prediction_id: string;
  raw_prediction: string;
  parsed_claim?: { statement: string; verification_date: string; date_reasoning: string };
  verification_plan?: { sources: string[]; criteria: string[]; steps: string[] };
  verifiability_score?: number;
  verifiability_reasoning?: string;
  score_tier?: string;
  score_label?: string;
  score_guidance?: string;
  dimension_assessments?: Array<{ dimension: string; score: number; reasoning: string }>;
  tier_display?: { color: string; icon: string; label: string };
  reviewable_sections?: ReviewSection[];
  status?: string;
}

const getScoreStyle = (score?: number) => {
  if (score === undefined || score === null) return { color: '#94a3b8', bg: '#1e293b', icon: '⚪' };
  if (score >= 0.8) return { color: '#4ade80', bg: '#052e16', icon: '🟢' };
  if (score >= 0.5) return { color: '#facc15', bg: '#422006', icon: '🟡' };
  return { color: '#f87171', bg: '#450a0a', icon: '🔴' };
};

const PredictionInput = () => {
  const [prompt, setPrompt] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamText, setStreamText] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [, setPredictionId] = useState<string | null>(null);
  const [bundle, setBundle] = useState<PredictionBundle | null>(null);
  const [currentTurn, setCurrentTurn] = useState<string>('');
  const [answers, setAnswers] = useState<Record<number, string>>({});
  const [isClarifying, setIsClarifying] = useState(false);
  useAuth(); // ensure auth context is available

  const handleSubmit = async () => {
    if (!prompt.trim()) return;
    setIsStreaming(true);
    setError(null);
    setStreamText('');
    setPredictionId(null);
    setBundle(null);
    setCurrentTurn('');

    try {
      const accessToken = localStorage.getItem('accessToken');
      if (!accessToken) { setError('Not authenticated'); setIsStreaming(false); return; }
      const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone;

      connectAndStream(accessToken, { prediction_text: prompt, timezone }, {
        onEvent: (event: StreamEvent) => {
          console.log('StreamEvent:', event.type, event.data?.turn_name || '', JSON.stringify(event.data || {}).substring(0, 100));
          switch (event.type) {
            case 'flow_started':
              setPredictionId(event.prediction_id);
              setStreamText('🔍 Parsing prediction...\n');
              setCurrentTurn('Parsing prediction...');
              break;
            case 'text':
              setStreamText(prev => prev + ((event.data?.content as string) || ''));
              break;
            case 'turn_complete': {
              const turnName = event.data?.turn_name as string;
              const nextLabel = turnName === 'parse' ? '\n\n📋 Building verification plan...\n'
                : turnName === 'plan' ? '\n\n📊 Scoring verifiability...\n'
                : turnName === 'review' ? '\n\n✅ Complete\n' : '\n\n';
              setStreamText(prev => prev + nextLabel);
              setCurrentTurn(turnName === 'review' ? 'Finalizing...' : nextLabel.trim());
              break;
            }
            case 'flow_complete':
              setBundle(event.data as unknown as PredictionBundle);
              setIsStreaming(false);
              setCurrentTurn('');
              setStreamText('');
              break;
            case 'error':
              setError((event.data?.message as string) || 'Agent error');
              setIsStreaming(false);
              setCurrentTurn('');
              break;
          }
        },
        onError: (err) => { setError(err); setIsStreaming(false); },
        onClose: () => { if (!bundle) setIsStreaming(false); },
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to connect');
      setIsStreaming(false);
    }
  };

  const handleClarificationSubmit = () => {
    if (!bundle?.prediction_id || !bundle?.reviewable_sections) return;
    const improvableSections = bundle.reviewable_sections.filter(s => s.improvable);
    const allQuestions = improvableSections.flatMap(s => s.questions);
    const clarificationAnswers = allQuestions.map((q, i) => ({
      question: q,
      answer: answers[i] || '',
    })).filter(a => a.answer.trim());

    if (clarificationAnswers.length === 0) return;

    setIsClarifying(true);
    setIsStreaming(true);
    setStreamText('');
    setCurrentTurn('Re-analyzing with your clarifications...');
    setError(null);

    try {
      const accessToken = localStorage.getItem('accessToken');
      if (!accessToken) { setError('Not authenticated'); setIsStreaming(false); setIsClarifying(false); return; }
      const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone;

      connectAndStream(accessToken, {
        prediction_id: bundle.prediction_id,
        clarification_answers: clarificationAnswers,
        timezone,
      } as never, {
        onEvent: (event: StreamEvent) => {
          switch (event.type) {
            case 'flow_started':
              setStreamText('🔄 Re-analyzing prediction...\n');
              setCurrentTurn('Parsing with clarifications...');
              break;
            case 'text':
              setStreamText(prev => prev + ((event.data?.content as string) || ''));
              break;
            case 'turn_complete': {
              const turnName = event.data?.turn_name as string;
              const nextLabel = turnName === 'parse' ? '\n\n📋 Rebuilding verification plan...\n'
                : turnName === 'plan' ? '\n\n📊 Re-scoring verifiability...\n'
                : turnName === 'review' ? '\n\n✅ Complete\n' : '\n\n';
              setStreamText(prev => prev + nextLabel);
              break;
            }
            case 'flow_complete':
              setBundle(event.data as unknown as PredictionBundle);
              setIsStreaming(false);
              setIsClarifying(false);
              setCurrentTurn('');
              setStreamText('');
              setAnswers({});
              break;
            case 'error':
              setError((event.data?.message as string) || 'Clarification error');
              setIsStreaming(false);
              setIsClarifying(false);
              break;
          }
        },
        onError: (err) => { setError(err); setIsStreaming(false); setIsClarifying(false); },
        onClose: () => { setIsStreaming(false); setIsClarifying(false); },
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to send clarification');
      setIsStreaming(false);
      setIsClarifying(false);
    }
  };

  const improvableSections = bundle?.reviewable_sections?.filter(s => s.improvable) || [];
  const allQuestions = improvableSections.flatMap(s => s.questions);

  const scoreStyle = getScoreStyle(bundle?.verifiability_score);

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
          {isStreaming ? 'Processing...' : 'Make Prediction'}
        </button>
      </div>

      {error && <div className="error-message">{error}</div>}

      {/* Streaming reasoning display */}
      {isStreaming && (
        <div className="streaming-response">
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '16px' }}>
            <h3 style={{ margin: 0, color: '#8fa4f3' }}>🧠 AI Reasoning</h3>
            <div className="processing-indicator">
              <span>{currentTurn || 'Processing'}</span>
              <span className="processing-dots"><span></span><span></span><span></span></span>
            </div>
          </div>
          {streamText && (
            <div style={{ padding: '16px', borderRadius: '8px', backgroundColor: 'rgba(15,23,42,0.8)', border: '1px solid rgba(102,126,234,0.2)', minHeight: '60px' }}>
              <p style={{ whiteSpace: 'pre-wrap', margin: 0, lineHeight: 1.6, color: '#cbd5e1' }}>{streamText}</p>
            </div>
          )}
        </div>
      )}

      {/* Structured result display */}
      {bundle && (
        <div style={{ marginTop: '20px' }}>
          <h3>Prediction Details</h3>
          <div className="structured-response">
            {/* Prediction Statement */}
            <div className="response-field">
              <h3>Prediction Statement</h3>
              <p>{bundle.parsed_claim?.statement || bundle.raw_prediction}</p>
            </div>

            {/* Dates */}
            <div className="response-field">
              <h3>Verification Date</h3>
              <p>{bundle.parsed_claim?.verification_date ? new Date(bundle.parsed_claim.verification_date).toLocaleString() : 'Not available'}</p>
              {bundle.parsed_claim?.date_reasoning && (
                <p style={{ fontStyle: 'italic', color: '#94a3b8', marginTop: '4px', fontSize: '14px' }}>
                  {bundle.parsed_claim.date_reasoning}
                </p>
              )}
            </div>

            {/* Verifiability Score */}
            {bundle.verifiability_score !== undefined && (
              <div className="response-field">
                <h3>Verifiability Score</h3>
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '8px' }}>
                  <span style={{
                    display: 'inline-flex', alignItems: 'center', gap: '6px',
                    padding: '6px 16px', borderRadius: '20px', fontSize: '16px', fontWeight: '600',
                    color: scoreStyle.color, backgroundColor: scoreStyle.bg,
                    border: `1px solid ${scoreStyle.color}20`
                  }}>
                    <span>{scoreStyle.icon}</span>
                    <span>{(bundle.verifiability_score * 100).toFixed(0)}%</span>
                    {bundle.score_label && <span style={{ fontWeight: '400', fontSize: '14px' }}>— {bundle.score_label}</span>}
                  </span>
                </div>
                {bundle.score_guidance && (
                  <p style={{ color: '#cbd5e1', fontSize: '14px', lineHeight: 1.5 }}>{bundle.score_guidance}</p>
                )}
                {bundle.verifiability_reasoning && (
                  <details style={{ marginTop: '8px' }}>
                    <summary style={{ cursor: 'pointer', color: '#60a5fa' }}>Detailed reasoning</summary>
                    <p style={{ marginTop: '8px', fontSize: '14px', color: '#94a3b8' }}>{bundle.verifiability_reasoning}</p>
                  </details>
                )}
              </div>
            )}

            {/* Dimension Assessments */}
            {bundle.dimension_assessments && bundle.dimension_assessments.length > 0 && (
              <div className="response-field">
                <h3>Score Dimensions</h3>
                {bundle.dimension_assessments.map((dim, i) => {
                  const dimStyle = getScoreStyle(dim.score);
                  return (
                    <div key={i} style={{ marginBottom: '8px', padding: '8px', borderRadius: '6px', backgroundColor: '#0f172a' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <strong style={{ fontSize: '14px', color: '#cbd5e1' }}>{dim.dimension}</strong>
                        <span style={{ color: dimStyle.color, fontWeight: '600' }}>{dimStyle.icon} {(dim.score * 100).toFixed(0)}%</span>
                      </div>
                      <p style={{ margin: '4px 0 0', fontSize: '13px', color: '#94a3b8' }}>{dim.reasoning}</p>
                    </div>
                  );
                })}
              </div>
            )}

            {/* Verification Plan */}
            {bundle.verification_plan && (
              <div className="response-field">
                <h3>Verification Plan</h3>
                <div className="verification-method">
                  <div className="method-section">
                    <h4>Sources:</h4>
                    <ul>
                      {bundle.verification_plan.sources?.map((s, i) => <li key={i}>{s}</li>) || <li>None</li>}
                    </ul>
                  </div>
                  <div className="method-section">
                    <h4>Criteria:</h4>
                    <ul>
                      {bundle.verification_plan.criteria?.map((c, i) => <li key={i}>{c}</li>) || <li>None</li>}
                    </ul>
                  </div>
                  <div className="method-section">
                    <h4>Steps:</h4>
                    <ul>
                      {bundle.verification_plan.steps?.map((s, i) => <li key={i}>{s}</li>) || <li>None</li>}
                    </ul>
                  </div>
                </div>
              </div>
            )}

            {/* Status */}
            <div className="response-field">
              <h3>Status</h3>
              <p>{bundle.status || 'pending'}</p>
            </div>
          </div>

          {/* Clarification Questions */}
          {allQuestions.length > 0 && !isClarifying && (
            <div style={{ marginTop: '20px', padding: '16px', borderRadius: '12px', backgroundColor: '#1e293b', border: '2px solid #3b82f6' }}>
              <h3 style={{ margin: '0 0 12px', color: '#60a5fa' }}>💬 Clarification Questions</h3>
              <p style={{ fontSize: '14px', color: '#94a3b8', marginBottom: '16px' }}>
                The agent identified assumptions in your prediction. Answering these questions will improve the verification plan.
              </p>
              {allQuestions.map((q, i) => (
                <div key={i} style={{ marginBottom: '16px' }}>
                  <label style={{ display: 'block', fontWeight: '600', marginBottom: '6px', fontSize: '14px', color: '#cbd5e1' }}>
                    {q}
                  </label>
                  <input
                    type="text"
                    value={answers[i] || ''}
                    onChange={(e) => setAnswers(prev => ({ ...prev, [i]: e.target.value }))}
                    placeholder="Your answer..."
                    style={{ width: '100%', padding: '8px 12px', borderRadius: '6px', border: '1px solid #334155', fontSize: '14px', boxSizing: 'border-box', backgroundColor: '#0f172a', color: '#e2e8f0' }}
                  />
                </div>
              ))}
              <button
                onClick={handleClarificationSubmit}
                disabled={Object.values(answers).every(a => !a?.trim())}
                className="send-button"
                style={{ marginTop: '8px' }}
              >
                Submit Clarifications
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default PredictionInput;
