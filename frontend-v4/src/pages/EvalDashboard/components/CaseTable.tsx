/** Data-driven case results table with expandable detail rows. */

import { useState } from 'react';
import type { CaseResult, AgentType } from '../types';
import { truncateText, getScoreColor } from '../utils';

interface Props {
  cases: CaseResult[];
  agentType: AgentType;
}

export default function CaseTable({ cases, agentType }: Props) {
  const [expandedId, setExpandedId] = useState<string | null>(null);

  if (cases.length === 0) return <p style={{ color: '#94a3b8' }}>No cases in this run.</p>;

  // Derive score columns from first case's scores keys (data-driven)
  const scoreKeys = cases[0]?.scores ? Object.keys(cases[0].scores) : [];

  const getText = (c: CaseResult) => c.input ?? c.prediction_text ?? '';

  return (
    <div style={{ overflowX: 'auto' }}>
      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.8rem' }}>
        <thead>
          <tr style={{ borderBottom: '2px solid #475569' }}>
            <th style={thStyle}>ID</th>
            <th style={thStyle}>Text</th>
            {agentType === 'verification' && <th style={thStyle}>Expected</th>}
            {agentType === 'calibration' && <th style={thStyle}>Score</th>}
            {agentType === 'calibration' && <th style={thStyle}>Tier</th>}
            {agentType === 'calibration' && <th style={thStyle}>Verdict</th>}
            {agentType === 'calibration' && <th style={thStyle}>Cal?</th>}
            {scoreKeys.map(k => <th key={k} style={thStyle}>{k}</th>)}
          </tr>
        </thead>
        <tbody>
          {cases.map(c => {
            const isExpanded = expandedId === c.id;
            const hasError = !!c.error;
            return (
              <tbody key={c.id}>
                <tr
                  onClick={() => setExpandedId(isExpanded ? null : c.id)}
                  style={{
                    cursor: 'pointer', borderBottom: '1px solid #334155',
                    background: hasError ? '#3b1111' : isExpanded ? '#1e293b' : 'transparent',
                  }}
                >
                  <td style={tdStyle}>{c.id}</td>
                  <td style={tdStyle}>{truncateText(getText(c))}</td>
                  {agentType === 'verification' && <td style={tdStyle}>{c.expected_verdict ?? ''}</td>}
                  {agentType === 'calibration' && (
                    <td style={tdStyle}>{c.verifiability_score?.toFixed(2) ?? 'ERR'}</td>
                  )}
                  {agentType === 'calibration' && <td style={tdStyle}>{c.score_tier ?? ''}</td>}
                  {agentType === 'calibration' && <td style={tdStyle}>{c.actual_verdict ?? 'ERR'}</td>}
                  {agentType === 'calibration' && (
                    <td style={tdStyle}>
                      {c.calibration_correct == null ? '—' : c.calibration_correct ? '✓' : '✗'}
                    </td>
                  )}
                  {scoreKeys.map(k => {
                    const s = c.scores?.[k];
                    if (!s) return <td key={k} style={tdStyle}>—</td>;
                    return (
                      <td key={k} style={{ ...tdStyle, color: getScoreColor(s.score) }}>
                        {s.score.toFixed(2)} {s.pass ? '' : '✗'}
                      </td>
                    );
                  })}
                </tr>
                {isExpanded && (
                  <tr>
                    <td colSpan={99} style={{ padding: '0.75rem 1rem', background: '#0f172a' }}>
                      <CaseDetail caseResult={c} />
                    </td>
                  </tr>
                )}
              </tbody>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function CaseDetail({ caseResult }: { caseResult: CaseResult }) {
  const text = caseResult.input ?? caseResult.prediction_text ?? '';
  return (
    <div style={{ fontSize: '0.8rem' }}>
      <p style={{ color: '#e2e8f0', marginBottom: '0.5rem' }}>{text}</p>
      {caseResult.error && (
        <p style={{ color: '#ef4444', marginBottom: '0.5rem' }}>Error: {caseResult.error}</p>
      )}
      {caseResult.scores && Object.entries(caseResult.scores).map(([name, s]) => (
        <div key={name} style={{ marginBottom: '0.5rem', paddingLeft: '0.5rem', borderLeft: `3px solid ${getScoreColor(s.score)}` }}>
          <div>
            <span style={{ fontWeight: 600, color: getScoreColor(s.score) }}>{name}: {s.score.toFixed(2)}</span>
            {!s.pass && <span style={{ color: '#ef4444', marginLeft: '0.5rem' }}>FAIL</span>}
          </div>
          <div style={{ color: '#94a3b8', marginTop: '0.25rem', whiteSpace: 'pre-wrap' }}>{s.reason}</div>
        </div>
      ))}
      {caseResult.calibration_correct != null && (
        <div style={{ marginTop: '0.5rem', color: '#94a3b8' }}>
          Calibration: {caseResult.calibration_correct ? '✓ correct' : '✗ incorrect'}
          {caseResult.creation_duration_seconds != null && ` | creation: ${caseResult.creation_duration_seconds}s`}
          {caseResult.verification_duration_seconds != null && ` | verification: ${caseResult.verification_duration_seconds}s`}
        </div>
      )}
    </div>
  );
}

const thStyle: React.CSSProperties = {
  textAlign: 'left', padding: '0.4rem 0.5rem', color: '#94a3b8', fontWeight: 600,
};
const tdStyle: React.CSSProperties = {
  padding: '0.4rem 0.5rem', color: '#e2e8f0',
};
