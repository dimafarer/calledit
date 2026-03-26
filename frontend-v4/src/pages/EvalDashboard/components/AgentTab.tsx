/**
 * AgentTab — Displays run selector, aggregate scores, and case table for one agent type.
 * Data-driven: renders whatever fields exist in the report.
 */

import { useState, useEffect } from 'react';
import { useReportList, getFullReport } from '../hooks/useReportStore';
import type { AgentType, FullReport, ReportSummary } from '../types';
import { formatRunLabel, sortByTimestampDesc } from '../utils';
import AggregateScores from './AggregateScores';
import CaseTable from './CaseTable';
import WarningBanner from './WarningBanner';
import CalibrationScatter from './CalibrationScatter';

interface Props {
  agentType: AgentType;
}

export default function AgentTab({ agentType }: Props) {
  const { reports, loading, error } = useReportList(agentType);
  const [selectedTimestamp, setSelectedTimestamp] = useState<string | null>(null);
  const [fullReport, setFullReport] = useState<FullReport | null>(null);
  const [loadingReport, setLoadingReport] = useState(false);

  const sorted = sortByTimestampDesc(reports);

  // Auto-select newest run when reports load
  useEffect(() => {
    if (sorted.length > 0) {
      setSelectedTimestamp(prev => prev ?? sorted[0].run_metadata.timestamp);
    }
  }, [reports]);

  // Reset selection when agent type changes
  useEffect(() => {
    setSelectedTimestamp(null);
    setFullReport(null);
  }, [agentType]);

  // Load full report when selection changes
  useEffect(() => {
    if (!selectedTimestamp) return;
    let cancelled = false;
    setLoadingReport(true);
    getFullReport(agentType, selectedTimestamp).then(report => {
      if (!cancelled) {
        setFullReport(report);
        setLoadingReport(false);
      }
    }).catch(() => {
      if (!cancelled) setLoadingReport(false);
    });
    return () => { cancelled = true; };
  }, [agentType, selectedTimestamp]);

  if (loading) return <p>Loading reports...</p>;
  if (error) return <p style={{ color: '#ef4444' }}>Error: {error}</p>;
  if (sorted.length === 0) return <p style={{ color: '#94a3b8' }}>No runs found for {agentType}.</p>;

  const selectedSummary = sorted.find(r => r.run_metadata.timestamp === selectedTimestamp);

  return (
    <div>
      {/* Run Selector */}
      <select
        value={selectedTimestamp ?? ''}
        onChange={e => setSelectedTimestamp(e.target.value)}
        style={{
          width: '100%', padding: '0.5rem', marginBottom: '1rem',
          background: '#1e293b', color: '#e2e8f0', border: '1px solid #475569',
          borderRadius: 4, fontSize: '0.85rem',
        }}
      >
        {sorted.map(r => (
          <option key={r.run_metadata.timestamp} value={r.run_metadata.timestamp}>
            {formatRunLabel(r.run_metadata)}
          </option>
        ))}
      </select>

      {/* Metadata */}
      {selectedSummary && <MetadataPanel meta={selectedSummary.run_metadata} />}

      {/* Warning Banners */}
      {selectedSummary && <WarningBanner metadata={selectedSummary.run_metadata} />}
      {fullReport?.bias_warning && (
        <div style={{ background: '#78350f', padding: '0.5rem 1rem', borderRadius: 4, marginBottom: '1rem', color: '#fef3c7' }}>
          ⚠ {fullReport.bias_warning}
        </div>
      )}

      {/* Aggregate Scores */}
      {selectedSummary && <AggregateScores scores={selectedSummary.aggregate_scores} />}

      {/* Calibration Scatter (calibration tab only) */}
      {agentType === 'calibration' && fullReport?.case_results && (
        <CalibrationScatter cases={fullReport.case_results} />
      )}

      {/* Case Table */}
      {loadingReport ? (
        <p>Loading case details...</p>
      ) : fullReport?.case_results ? (
        <CaseTable cases={fullReport.case_results} agentType={agentType} />
      ) : null}
    </div>
  );
}

function MetadataPanel({ meta }: { meta: ReportSummary['run_metadata'] }) {
  const fields = Object.entries(meta).filter(
    ([k, v]) => v != null && k !== 'description' && k !== 'ground_truth_limitation' && k !== 'bias_warning',
  );
  return (
    <div style={{
      display: 'flex', flexWrap: 'wrap', gap: '0.5rem 1.5rem',
      marginBottom: '1rem', fontSize: '0.8rem', color: '#94a3b8',
    }}>
      {fields.map(([k, v]) => (
        <span key={k}>
          <span style={{ color: '#64748b' }}>{k}:</span>{' '}
          {typeof v === 'object' ? JSON.stringify(v) : String(v)}
        </span>
      ))}
    </div>
  );
}
