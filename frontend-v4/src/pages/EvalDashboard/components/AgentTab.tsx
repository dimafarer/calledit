/**
 * AgentTab — Displays run selector, aggregate scores, and case table for one agent type.
 * Data-driven: renders whatever fields exist in the report.
 */

import { useState, useEffect } from 'react';
import { useAuth } from '../../../contexts/AuthContext';
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
  const { getToken } = useAuth();
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
    getFullReport(agentType, selectedTimestamp, getToken()).then(report => {
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

      {/* Calibration Scatter — the key narrative chart (unified and calibration tabs) */}
      {(agentType === 'calibration' || agentType === 'unified') && fullReport?.case_results && (
        <CalibrationScatter cases={fullReport.case_results} />
      )}

      {/* Aggregate Scores */}
      {selectedSummary && agentType !== 'unified' && <AggregateScores scores={selectedSummary.aggregate_scores} />}

      {/* Unified Pipeline: Three score sections */}
      {agentType === 'unified' && fullReport && (
        <UnifiedScoreSections report={fullReport} />
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
  // Always-visible summary fields
  const summaryKeys = ['agent', 'run_tier', 'case_count', 'duration_seconds', 'dataset_version'];
  const summaryFields = summaryKeys
    .filter(k => meta[k as keyof typeof meta] != null)
    .map(k => [k, meta[k as keyof typeof meta]] as [string, unknown]);

  // Everything else goes in the accordion
  const detailFields = Object.entries(meta).filter(
    ([k, v]) => v != null && !summaryKeys.includes(k) && k !== 'description' && k !== 'ground_truth_limitation' && k !== 'bias_warning',
  );

  const renderValue = (v: unknown) => typeof v === 'object' ? JSON.stringify(v) : String(v);

  return (
    <div style={{ marginBottom: '1rem', fontSize: '0.8rem', color: '#94a3b8' }}>
      {/* Always visible */}
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.4rem 1.5rem' }}>
        {summaryFields.map(([k, v]) => (
          <span key={k}>
            <span style={{ color: '#64748b' }}>{k}:</span> {renderValue(v)}
          </span>
        ))}
      </div>

      {/* Collapsible detail */}
      {detailFields.length > 0 && (
        <details style={{ marginTop: '0.5rem' }}>
          <summary style={{ cursor: 'pointer', color: '#64748b', fontSize: '0.8rem', userSelect: 'none' }}>
            + {detailFields.length} more fields
          </summary>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.4rem 1.5rem', marginTop: '0.5rem' }}>
            {detailFields.map(([k, v]) => (
              <span key={k}>
                <span style={{ color: '#64748b' }}>{k}:</span> {renderValue(v)}
              </span>
            ))}
          </div>
        </details>
      )}
    </div>
  );
}

function UnifiedScoreSections({ report }: { report: FullReport }) {
  const raw = report as unknown as Record<string, unknown>;
  const creation = raw.creation_scores as Record<string, number> | undefined;
  const verification = raw.verification_scores as Record<string, number> | undefined;
  const calibration = raw.calibration_scores as Record<string, unknown> | undefined;
  const phases = (report.run_metadata as unknown as Record<string, unknown>).phase_durations as Record<string, number> | undefined;

  const scoreColor = (v: number) => v >= 0.9 ? '#22c55e' : v >= 0.7 ? '#eab308' : '#ef4444';

  const renderScoreRow = (name: string, value: number | null | undefined) => {
    if (value == null) return null;
    return (
      <div key={name} style={{ display: 'flex', justifyContent: 'space-between', padding: '0.2rem 0' }}>
        <span style={{ color: '#94a3b8' }}>{name}</span>
        <span style={{ color: scoreColor(value), fontWeight: 600 }}>{value.toFixed(2)}</span>
      </div>
    );
  };

  return (
    <div style={{ marginBottom: '1.5rem' }}>
      {/* Phase Timing */}
      {phases && (
        <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1rem', flexWrap: 'wrap' }}>
          {Object.entries(phases).map(([k, v]) => (
            <div key={k} style={{ padding: '0.3rem 0.6rem', background: '#1e293b', borderRadius: 4, fontSize: '0.75rem', color: '#94a3b8' }}>
              {k.replace('_seconds', '')}: {v}s
            </div>
          ))}
        </div>
      )}

      {/* Three score sections */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '1rem' }}>
        {/* Creation */}
        <div style={{ background: '#1e293b', borderRadius: 6, padding: '0.8rem', border: '1px solid #334155' }}>
          <h4 style={{ margin: '0 0 0.5rem', color: '#60a5fa', fontSize: '0.85rem' }}>Creation</h4>
          {creation && Object.entries(creation).map(([k, v]) =>
            typeof v === 'number' ? renderScoreRow(k, v) : null
          )}
        </div>

        {/* Verification */}
        <div style={{ background: '#1e293b', borderRadius: 6, padding: '0.8rem', border: '1px solid #334155' }}>
          <h4 style={{ margin: '0 0 0.5rem', color: '#a78bfa', fontSize: '0.85rem' }}>Verification</h4>
          {verification && Object.entries(verification).map(([k, v]) =>
            typeof v === 'number' ? renderScoreRow(k, v) : null
          )}
        </div>

        {/* Calibration */}
        <div style={{ background: '#1e293b', borderRadius: 6, padding: '0.8rem', border: '1px solid #334155' }}>
          <h4 style={{ margin: '0 0 0.5rem', color: '#f59e0b', fontSize: '0.85rem' }}>Calibration</h4>
          {calibration && Object.entries(calibration).map(([k, v]) => {
            if (typeof v === 'number') return renderScoreRow(k, v);
            if (k === 'verdict_distribution' && typeof v === 'object' && v !== null) {
              const dist = v as Record<string, number>;
              const resolved = (dist.confirmed || 0) + (dist.refuted || 0);
              const failed = (dist.inconclusive || 0);
              const errors = (dist.creation_error || 0) + (dist.verification_error || 0);
              return (
                <div key={k} style={{ padding: '0.2rem 0' }}>
                  <span style={{ color: '#94a3b8', fontSize: '0.8rem' }}>outcomes: </span>
                  <span style={{ color: '#22c55e', fontSize: '0.8rem', marginLeft: '0.3rem' }}>resolved={resolved}</span>
                  <span style={{ color: '#64748b', fontSize: '0.75rem', marginLeft: '0.2rem' }}>({dist.confirmed || 0}✓ {dist.refuted || 0}✗)</span>
                  {failed > 0 && <span style={{ color: '#ef4444', fontSize: '0.8rem', marginLeft: '0.3rem' }}>inconclusive={failed}</span>}
                  {errors > 0 && <span style={{ color: '#f59e0b', fontSize: '0.8rem', marginLeft: '0.3rem' }}>errors={errors}</span>}
                </div>
              );
            }
            if (typeof v === 'object' && v !== null) {
              return (
                <div key={k} style={{ padding: '0.2rem 0' }}>
                  <span style={{ color: '#94a3b8', fontSize: '0.8rem' }}>{k}: </span>
                  {Object.entries(v as Record<string, number>).filter(([, n]) => n > 0).map(([vk, vv]) => (
                    <span key={vk} style={{ color: '#e2e8f0', fontSize: '0.8rem', marginLeft: '0.3rem' }}>{vk}={vv}</span>
                  ))}
                </div>
              );
            }
            return null;
          })}
        </div>
      </div>
    </div>
  );
}
