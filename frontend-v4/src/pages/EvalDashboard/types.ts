/** Eval Dashboard TypeScript interfaces for report schemas. */

export interface RunMetadata {
  description: string;
  agent: 'creation' | 'verification' | 'calibration' | string;
  run_tier: string;
  timestamp: string;
  duration_seconds: number;
  case_count: number;
  dataset_version?: string;
  prompt_versions?: Record<string, string>;
  model_id?: string;
  git_commit?: string;
  agent_runtime_arn?: string;
  features?: Record<string, unknown>;
  source?: string;
  ground_truth_limitation?: string;
  bias_warning?: string;
}

export interface ReportSummary {
  run_metadata: RunMetadata;
  aggregate_scores?: Record<string, number | Record<string, number> | null>;
  // New SDK format
  creation_scores?: Record<string, number>;
  verification_scores?: Record<string, number>;
  calibration_scores?: Record<string, number | Record<string, number>>;
}

export interface CaseScore {
  score: number;
  pass: boolean;
  reason: string;
}

export interface CaseResult {
  id: string;
  scores?: Record<string, CaseScore>;
  error?: string | null;
  // Creation-specific
  input?: string;
  prediction_id?: string;
  // Verification-specific
  prediction_text?: string;
  expected_verdict?: string;
  // Calibration-specific
  verifiability_score?: number;
  score_tier?: string;
  actual_verdict?: string;
  actual_confidence?: number;
  calibration_correct?: boolean;
  creation_duration_seconds?: number;
  verification_duration_seconds?: number;
}

export interface FullReport extends ReportSummary {
  case_results: CaseResult[];
  bias_warning?: string;
}

export type AgentType = 'creation' | 'verification' | 'calibration' | 'unified';

export const AGENT_TABS: { key: AgentType; label: string }[] = [
  { key: 'unified', label: 'Unified Pipeline' },
  { key: 'creation', label: 'Creation Agent' },
  { key: 'verification', label: 'Verification Agent' },
  { key: 'calibration', label: 'Cross-Agent Calibration' },
];
