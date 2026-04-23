/**
 * ContinuousTab — Wraps AgentTab with continuous-specific charts.
 * Shows ResolutionRateChart (all reports) and ResolutionSpeedChart (selected report)
 * above the standard AgentTab content (run selector, scores, case table).
 */

import { useReportList } from '../hooks/useReportStore';
import { sortByTimestampDesc } from '../utils';
import type { ContinuousCalibrationScores } from '../types';
import AgentTab from './AgentTab';
import ResolutionRateChart from './ResolutionRateChart';
import ResolutionSpeedChart from './ResolutionSpeedChart';

export default function ContinuousTab() {
  const { reports, loading } = useReportList('continuous');
  const sorted = sortByTimestampDesc(reports);

  // Extract resolution_speed_by_tier from the newest report
  const newestCal = sorted[0]?.calibration_scores as ContinuousCalibrationScores | undefined;

  return (
    <div>
      {/* Continuous-specific charts */}
      {!loading && (
        <div style={{ marginBottom: '1.5rem' }}>
          <ResolutionRateChart reports={sorted} />
          <ResolutionSpeedChart resolutionSpeedByTier={newestCal?.resolution_speed_by_tier} />
        </div>
      )}

      {/* Standard AgentTab: run selector, metadata, scores, case table */}
      <AgentTab agentType="continuous" />
    </div>
  );
}
