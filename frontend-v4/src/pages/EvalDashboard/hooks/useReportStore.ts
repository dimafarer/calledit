/**
 * React hooks for reading eval reports.
 * Dev mode: calls Vite dev server proxy (/api/eval/*)
 * Production: will call API Gateway (future)
 */

import { useState, useEffect, useCallback } from 'react';
import type { ReportSummary, FullReport, AgentType } from '../types';

/** List all reports for an agent type (metadata + scores only, no case_results) */
export function useReportList(agentType: AgentType) {
  const [reports, setReports] = useState<ReportSummary[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchReports = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`/api/eval/reports?agent=${agentType}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}: ${await res.text()}`);
      const items = await res.json();
      setReports(items);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load reports');
      setReports([]);
    } finally {
      setLoading(false);
    }
  }, [agentType]);

  useEffect(() => { fetchReports(); }, [fetchReports]);

  return { reports, loading, error, refresh: fetchReports };
}

/** Get a full report including case_results */
export async function getFullReport(
  agentType: AgentType,
  timestamp: string,
): Promise<FullReport | null> {
  const res = await fetch(`/api/eval/report?agent=${agentType}&ts=${encodeURIComponent(timestamp)}`);
  if (res.status === 404) return null;
  if (!res.ok) throw new Error(`HTTP ${res.status}: ${await res.text()}`);
  return res.json();
}
