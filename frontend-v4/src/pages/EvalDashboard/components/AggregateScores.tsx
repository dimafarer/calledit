/** Data-driven aggregate score bars — renders whatever keys exist in aggregate_scores. */

import { getScoreColor, isNumericScore } from '../utils';

interface Props {
  scores: Record<string, number | Record<string, number> | null>;
}

export default function AggregateScores({ scores }: Props) {
  const entries = Object.entries(scores).filter(([, v]) => v != null);
  if (entries.length === 0) return null;

  return (
    <div style={{ marginBottom: '1.5rem' }}>
      <h3 style={{ margin: '0 0 0.5rem', fontSize: '0.9rem', color: '#94a3b8' }}>Aggregate Scores</h3>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
        {entries.map(([name, value]) => {
          if (isNumericScore(value)) {
            return (
              <div key={name} style={{
                padding: '0.4rem 0.8rem', borderRadius: 4,
                background: '#1e293b', border: `2px solid ${getScoreColor(value)}`,
                fontSize: '0.8rem',
              }}>
                <span style={{ color: '#94a3b8' }}>{name}: </span>
                <span style={{ color: getScoreColor(value), fontWeight: 600 }}>
                  {value.toFixed(2)}
                </span>
              </div>
            );
          }
          // Nested object (e.g., verdict_distribution)
          if (typeof value === 'object' && value !== null) {
            return (
              <div key={name} style={{
                padding: '0.4rem 0.8rem', borderRadius: 4,
                background: '#1e293b', border: '1px solid #475569',
                fontSize: '0.8rem',
              }}>
                <span style={{ color: '#94a3b8' }}>{name}: </span>
                {Object.entries(value).filter(([, v]) => v > 0).map(([k, v]) => (
                  <span key={k} style={{ marginLeft: '0.3rem', color: '#e2e8f0' }}>
                    {k}={v}
                  </span>
                ))}
              </div>
            );
          }
          return null;
        })}
      </div>
    </div>
  );
}
