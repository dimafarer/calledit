import { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { fetchPredictions } from '../services/agentCoreWebSocket';

interface Prediction {
  prediction_id: string;
  raw_prediction: string;
  prediction_statement?: string;
  status: string;
  verification_date: string;
  verifiability_score?: number;
  created_at: string;
  verification_result?: {
    verdict: string;
    confidence: number;
    reasoning: string;
  };
}

const ListPredictions = () => {
  const [predictions, setPredictions] = useState<Prediction[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { isAuthenticated, getToken } = useAuth();

  useEffect(() => {
    if (!isAuthenticated) return;
    const load = async () => {
      setIsLoading(true);
      setError(null);
      try {
        const token = getToken();
        if (!token) { setError('Not authenticated'); return; }
        const results = await fetchPredictions(token);
        setPredictions(results);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load predictions');
      } finally {
        setIsLoading(false);
      }
    };
    load();
  }, [isAuthenticated]);

  const formatDate = (dateStr: string) => {
    if (!dateStr) return 'N/A';
    try { return new Date(dateStr).toLocaleString(); } catch { return dateStr; }
  };

  const getScoreColor = (score?: number) => {
    if (score === undefined || score === null) return '#94a3b8';
    if (score >= 0.8) return '#4ade80';
    if (score >= 0.5) return '#facc15';
    return '#f87171';
  };

  return (
    <div className="list-predictions-container">
      <h2>My Predictions</h2>
      {isLoading && <div className="loading" role="status">Loading predictions...</div>}
      {error && <div className="error-message">{error}</div>}
      {!isLoading && !error && (
        <div className="predictions-list">
          {predictions.length > 0 ? predictions.map((p) => (
            <div key={p.prediction_id} className="prediction-card">
              <h3>{p.prediction_statement || p.raw_prediction}</h3>
              <div className="prediction-details">
                <p><strong>Created:</strong> {formatDate(p.created_at)}</p>
                <p><strong>Verification Date:</strong> {formatDate(p.verification_date)}</p>
                <p><strong>Status:</strong> {p.status}</p>
                {p.verifiability_score !== undefined && (
                  <p>
                    <strong>Verifiability:</strong>{' '}
                    <span style={{ color: getScoreColor(p.verifiability_score), fontWeight: 600 }}>
                      {(p.verifiability_score * 100).toFixed(0)}%
                    </span>
                  </p>
                )}
                {p.verification_result && (
                  <details>
                    <summary>Verification Result</summary>
                    <div className="verification-details">
                      <p><strong>Verdict:</strong> {p.verification_result.verdict}</p>
                      <p><strong>Confidence:</strong> {(p.verification_result.confidence * 100).toFixed(1)}%</p>
                      <p>{p.verification_result.reasoning}</p>
                    </div>
                  </details>
                )}
              </div>
            </div>
          )) : (
            <div className="no-predictions"><p>No predictions yet.</p></div>
          )}
        </div>
      )}
    </div>
  );
};

export default ListPredictions;
