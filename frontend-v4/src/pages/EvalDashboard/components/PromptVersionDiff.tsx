/** Highlights changed prompt versions between two runs. */

import { diffPromptVersions } from '../utils';

interface Props {
  versionsA?: Record<string, string>;
  versionsB?: Record<string, string>;
  labelA?: string;
  labelB?: string;
}

export default function PromptVersionDiff({ versionsA, versionsB, labelA = 'Run A', labelB = 'Run B' }: Props) {
  const changed = diffPromptVersions(versionsA, versionsB);
  if (changed.length === 0) {
    return <p style={{ color: '#94a3b8', fontSize: '0.8rem' }}>No prompt version changes between runs.</p>;
  }

  return (
    <div style={{ marginBottom: '1rem', fontSize: '0.8rem' }}>
      <h4 style={{ margin: '0 0 0.3rem', color: '#94a3b8' }}>Prompt Version Changes</h4>
      <table style={{ borderCollapse: 'collapse' }}>
        <thead>
          <tr style={{ borderBottom: '1px solid #475569' }}>
            <th style={thStyle}>Prompt</th>
            <th style={thStyle}>{labelA}</th>
            <th style={thStyle}>{labelB}</th>
          </tr>
        </thead>
        <tbody>
          {changed.map(key => (
            <tr key={key} style={{ borderBottom: '1px solid #334155' }}>
              <td style={tdStyle}>{key}</td>
              <td style={{ ...tdStyle, color: '#ef4444' }}>{versionsA?.[key] ?? '—'}</td>
              <td style={{ ...tdStyle, color: '#22c55e' }}>{versionsB?.[key] ?? '—'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

const thStyle: React.CSSProperties = { textAlign: 'left', padding: '0.3rem 0.8rem', color: '#94a3b8' };
const tdStyle: React.CSSProperties = { padding: '0.3rem 0.8rem', color: '#e2e8f0' };
