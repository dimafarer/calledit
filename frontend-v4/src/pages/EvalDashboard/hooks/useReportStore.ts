/**
 * React hooks for reading eval reports.
 * Dev mode: calls Vite dev server proxy (/api/eval/*)
 * Production: calls API Gateway with Cognito JWT auth
 */

import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../../../contexts/AuthContext';
import type { ReportSummary, FullReport, AgentType } from '../types';

// Dev: Vite proxy at /api, Prod: API Gateway URL
const BASE_URL = import.meta.env.DEV
  ? '/api'
  : import.meta.env.VITE_V4_API_URL;

function useAuthHeaders(): () => Record<string, string> {
  const { getToken } = useAuth();
  return (): Record<string, string> => {
    if (import.meta.env.DEV) return {};
    const token = getToken();
    if (!token) return {};
    return { Authorization: `Bearer ${token}` };
  };
}

/** List all reports for an agent type (metadata + scores only, no case_results) */
export function useReportList(agentType: AgentType) {
  const [reports, setReports] = useState<ReportSummary[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const getHeaders = useAuthHeaders();

  const fetchReports = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(
        `${BASE_URL}/eval/reports?agent=${agentType}`,
        { headers: getHeaders() },
      );
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
  token?: string | null,
): Promise<FullReport | null> {
  const headers: HeadersInit = {};
  if (!import.meta.env.DEV && token) {
    headers.Authorization = `Bearer ${token}`;
  }

  const res = await fetch(
    `${BASE_URL}/eval/report?agent=${agentType}&ts=${encodeURIComponent(timestamp)}`,
    { headers },
  );
  if (res.status === 404) return null;
  if (!res.ok) throw new Error(`HTTP ${res.status}: ${await res.text()}`);
  return res.json();
}
