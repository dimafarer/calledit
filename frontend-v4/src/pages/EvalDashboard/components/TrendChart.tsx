/** Multi-run trend chart — overlay aggregate scores across selected runs. */

import { useMemo } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import type { ReportSummary } from '../types';
import { isNumericScore } from '../utils';

const COLORS = ['#3b82f6', '#22c55e', '#eab308', '#ef4444', '#a855f7', '#06b6d4', '#f97316', '#ec4899'];

interface Props {
  reports: ReportSummary[];
  metricKeys?: string[];
}

export default function TrendChart({ reports, metricKeys }: Props) {
  // Derive available metric keys from all reports
  const availableKeys = useMemo(() => {
    const keys = new Set<string>();
    reports.forEach(r => {
      Object.entries(r.aggregate_scores).forEach(([k, v]) => {
        if (isNumericScore(v)) keys.add(k);
      });
    });
    return [...keys].sort();
  }, [reports]);

  const keysToPlot = metricKeys ?? availableKeys;

  // Build chart data: one point per report, sorted by timestamp ascending
  const data = useMemo(() => {
    return [...reports]
      .sort((a, b) => a.run_metadata.timestamp.localeCompare(b.run_metadata.timestamp))
      .map(r => {
        const point: Record<string, string | number> = {
          label: r.run_metadata.timestamp.slice(5, 16), // "MM-DDTHH:MM"
          fullTimestamp: r.run_metadata.timestamp,
        };
        keysToPlot.forEach(k => {
          const v = r.aggregate_scores[k];
          if (isNumericScore(v)) point[k] = v;
        });
        return point;
      });
  }, [reports, keysToPlot]);

  if (data.length < 2) return <p style={{ color: '#94a3b8', fontSize: '0.85rem' }}>Need 2+ runs for trend chart.</p>;

  return (
    <div style={{ marginBottom: '1.5rem' }}>
      <h3 style={{ margin: '0 0 0.5rem', fontSize: '0.9rem', color: '#94a3b8' }}>Score Trends Across Runs</h3>
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={data} margin={{ top: 10, right: 30, bottom: 30, left: 10 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
          <XAxis dataKey="label" stroke="#64748b" fontSize={11} />
          <YAxis domain={[0, 1]} stroke="#64748b" />
          <Tooltip
            contentStyle={{ background: '#1e293b', border: '1px solid #475569', fontSize: '0.8rem' }}
            labelStyle={{ color: '#e2e8f0' }}
          />
          <Legend wrapperStyle={{ fontSize: '0.8rem' }} />
          {keysToPlot.map((k, i) => (
            <Line
              key={k}
              type="monotone"
              dataKey={k}
              stroke={COLORS[i % COLORS.length]}
              strokeWidth={2}
              dot={{ r: 4 }}
              connectNulls
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
