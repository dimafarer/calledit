/** Resolution rate + stale inconclusive rate over verification passes. */

import { useMemo } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import type { ReportSummary } from '../types';

interface Props {
  reports: ReportSummary[];
}

export default function ResolutionRateChart({ reports }: Props) {
  const data = useMemo(() => {
    return reports
      .filter(r => r.run_metadata?.timestamp)
      .sort((a, b) => a.run_metadata.timestamp.localeCompare(b.run_metadata.timestamp))
      .map(r => {
        const cal = r.calibration_scores as Record<string, unknown> ?? {};
        const meta = r.run_metadata as unknown as Record<string, unknown>;
        return {
          pass: (meta.pass_number as number) ?? 0,
          label: `Pass ${(meta.pass_number as number) ?? '?'}`,
          timestamp: r.run_metadata.timestamp.slice(0, 19),
          resolution_rate: typeof cal.resolution_rate === 'number' ? cal.resolution_rate : null,
          stale_inconclusive_rate: typeof cal.stale_inconclusive_rate === 'number' ? cal.stale_inconclusive_rate : null,
        };
      });
  }, [reports]);

  if (data.length < 2) {
    return (
      <p style={{ color: '#94a3b8', fontSize: '0.85rem', marginBottom: '1rem' }}>
        Insufficient data for chart — need at least 2 continuous eval passes.
      </p>
    );
  }

  return (
    <div style={{ marginBottom: '1.5rem' }}>
      <h3 style={{ margin: '0 0 0.5rem', fontSize: '0.9rem', color: '#94a3b8' }}>Resolution Rate Over Passes</h3>
      <ResponsiveContainer width="100%" height={280}>
        <LineChart data={data} margin={{ top: 10, right: 30, bottom: 30, left: 10 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
          <XAxis dataKey="label" stroke="#64748b" fontSize={11} />
          <YAxis domain={[-0.05, 1.05]} stroke="#64748b" />
          <Tooltip
            contentStyle={{ background: '#1e293b', border: '1px solid #475569', fontSize: '0.8rem' }}
            labelStyle={{ color: '#e2e8f0' }}
            labelFormatter={(_, payload) => (payload?.[0]?.payload as Record<string, string>)?.timestamp ?? ''}
          />
          <Legend wrapperStyle={{ fontSize: '0.8rem' }} />
          <Line type="monotone" dataKey="resolution_rate" name="Resolution Rate"
            stroke="#22c55e" strokeWidth={2} dot={{ r: 6 }} connectNulls />
          <Line type="monotone" dataKey="stale_inconclusive_rate" name="Stale Inconclusive"
            stroke="#ef4444" strokeWidth={2} dot={{ r: 6 }} connectNulls />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
