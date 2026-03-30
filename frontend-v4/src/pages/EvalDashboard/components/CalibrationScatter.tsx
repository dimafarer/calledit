/** Scatter plot: verifiability_score (x) vs verification outcome (y).
 *  Adds small y-jitter to separate overlapping points at the same coordinates.
 */

import { ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import type { CaseResult } from '../types';
import { verdictToNumeric } from '../utils';

interface Props {
  cases: CaseResult[];
}

export default function CalibrationScatter({ cases }: Props) {
  const raw = cases
    .filter(c => !c.error && c.verifiability_score != null && c.actual_verdict)
    .map(c => ({
      id: c.id,
      x: c.verifiability_score!,
      y: verdictToNumeric(c.actual_verdict!),
      verdict: c.actual_verdict!,
      correct: c.calibration_correct,
    }));

  // Add jitter to separate overlapping points
  const seen = new Map<string, number>();
  const data = raw.map(d => {
    const key = `${d.x.toFixed(3)}_${d.y}`;
    const count = seen.get(key) ?? 0;
    seen.set(key, count + 1);
    // Spread overlapping points with small y-offset (±0.03 per overlap)
    const jitter = count === 0 ? 0 : (count % 2 === 1 ? 1 : -1) * Math.ceil(count / 2) * 0.03;
    return { ...d, yJittered: d.y + jitter };
  });

  if (data.length === 0) {
    return <p style={{ color: '#94a3b8' }}>No valid cases for scatter plot.</p>;
  }

  return (
    <div style={{ marginBottom: '1.5rem' }}>
      <h3 style={{ margin: '0 0 0.5rem', fontSize: '0.9rem', color: '#94a3b8' }}>
        Calibration: Verifiability Score vs Verification Outcome ({data.length} cases)
      </h3>
      <ResponsiveContainer width="100%" height={300}>
        <ScatterChart margin={{ top: 10, right: 30, bottom: 30, left: 10 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
          <XAxis
            type="number" dataKey="x" name="Verifiability Score"
            domain={[0, 1]} ticks={[0, 0.2, 0.4, 0.6, 0.8, 1.0]}
            label={{ value: 'Verifiability Score', position: 'bottom', fill: '#94a3b8' }}
            stroke="#64748b"
          />
          <YAxis
            type="number" dataKey="yJittered" name="Outcome"
            domain={[-0.15, 1.15]}
            ticks={[0, 0.5, 1.0]}
            tickFormatter={v => v === 1 ? 'confirmed' : v === 0.5 ? 'inconclusive' : v === 0 ? 'refuted' : ''}
            stroke="#64748b" width={80}
          />
          <Tooltip
            content={({ payload }) => {
              if (!payload?.length) return null;
              const d = payload[0].payload;
              return (
                <div style={{ background: '#1e293b', padding: '0.5rem', borderRadius: 4, border: '1px solid #475569', fontSize: '0.8rem' }}>
                  <div style={{ color: '#e2e8f0' }}>{d.id}</div>
                  <div style={{ color: '#94a3b8' }}>score: {d.x.toFixed(2)} → {d.verdict}</div>
                  <div style={{ color: d.correct ? '#22c55e' : '#ef4444' }}>
                    {d.correct ? '✓ calibrated' : '✗ miscalibrated'}
                  </div>
                </div>
              );
            }}
          />
          <Scatter data={data}>
            {data.map((d, i) => (
              <Cell key={i} fill={d.correct ? '#22c55e' : '#ef4444'} r={8} />
            ))}
          </Scatter>
        </ScatterChart>
      </ResponsiveContainer>
    </div>
  );
}
