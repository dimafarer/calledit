/** Resolution speed by V-score tier — grouped bar chart. */

import { useMemo } from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell, LabelList } from 'recharts';

interface Props {
  resolutionSpeedByTier: {
    high: number | null;
    moderate: number | null;
    low: number | null;
  } | undefined;
}

const TIER_COLORS: Record<string, string> = {
  high: '#22c55e',
  moderate: '#eab308',
  low: '#ef4444',
};

export default function ResolutionSpeedChart({ resolutionSpeedByTier }: Props) {
  const data = useMemo(() => {
    if (!resolutionSpeedByTier) return [];
    return [
      { tier: 'High (≥0.7)', value: resolutionSpeedByTier.high, key: 'high' },
      { tier: 'Moderate (0.4–0.7)', value: resolutionSpeedByTier.moderate, key: 'moderate' },
      { tier: 'Low (<0.4)', value: resolutionSpeedByTier.low, key: 'low' },
    ];
  }, [resolutionSpeedByTier]);

  if (!resolutionSpeedByTier) {
    return <p style={{ color: '#94a3b8', fontSize: '0.85rem' }}>No resolution speed data available.</p>;
  }

  const maxVal = Math.max(
    ...data.map(d => d.value ?? 0).filter(v => v > 0),
    1,
  );

  return (
    <div style={{ marginBottom: '1.5rem' }}>
      <h3 style={{ margin: '0 0 0.5rem', fontSize: '0.9rem', color: '#94a3b8' }}>
        Resolution Speed by V-Score Tier (median pass #)
      </h3>
      <ResponsiveContainer width="100%" height={220}>
        <BarChart data={data} margin={{ top: 20, right: 30, bottom: 10, left: 10 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
          <XAxis dataKey="tier" stroke="#64748b" fontSize={11} />
          <YAxis domain={[0, maxVal + 1]} stroke="#64748b" label={{ value: 'Pass #', angle: -90, position: 'insideLeft', style: { fill: '#64748b', fontSize: 11 } }} />
          <Tooltip
            contentStyle={{ background: '#1e293b', border: '1px solid #475569', fontSize: '0.8rem' }}
            formatter={(value: unknown) => value != null && typeof value === 'number' ? [value.toFixed(1), 'Median Pass'] : ['N/A', 'Median Pass']}
          />
          <Bar dataKey="value" radius={[4, 4, 0, 0]}>
            {data.map((entry) => (
              <Cell key={entry.key} fill={entry.value != null ? TIER_COLORS[entry.key] : '#334155'} />
            ))}
            <LabelList
              dataKey="value"
              position="top"
              style={{ fill: '#e2e8f0', fontSize: 12, fontWeight: 600 }}
              formatter={(value: unknown) => value != null && typeof value === 'number' ? value.toFixed(1) : 'N/A'}
            />
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
