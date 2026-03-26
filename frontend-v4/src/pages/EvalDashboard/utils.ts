/** Eval Dashboard utility functions — data-driven, no hardcoded evaluator names. */

import type { RunMetadata } from './types';

/** Score color coding: green >= 0.8, yellow >= 0.5, red < 0.5 */
export function getScoreColor(score: number): string {
  if (score >= 0.8) return '#22c55e'; // green
  if (score >= 0.5) return '#eab308'; // yellow
  return '#ef4444'; // red
}

/** Truncate text to maxLen chars with "..." suffix */
export function truncateText(text: string, maxLen = 60): string {
  if (text.length <= maxLen) return text;
  return text.slice(0, maxLen) + '...';
}

/** Format run selector label: "timestamp | agent | tier | description" */
export function formatRunLabel(meta: RunMetadata): string {
  const ts = meta.timestamp?.slice(0, 19) ?? 'unknown';
  return `${ts} | ${meta.agent} | ${meta.run_tier} | ${meta.description ?? ''}`;
}

/** Map verdict string to numeric value for scatter plot */
export function verdictToNumeric(verdict: string): number {
  if (verdict === 'confirmed') return 1.0;
  if (verdict === 'inconclusive') return 0.5;
  if (verdict === 'refuted') return 0.0;
  return -1; // error/unknown
}

/** Diff two prompt_versions dicts — returns keys that changed */
export function diffPromptVersions(
  a: Record<string, string> | undefined,
  b: Record<string, string> | undefined,
): string[] {
  const aMap = a ?? {};
  const bMap = b ?? {};
  const allKeys = new Set([...Object.keys(aMap), ...Object.keys(bMap)]);
  return [...allKeys].filter(k => aMap[k] !== bMap[k]);
}

/** Sort reports by timestamp descending (newest first) */
export function sortByTimestampDesc<T extends { run_metadata: RunMetadata }>(
  reports: T[],
): T[] {
  return [...reports].sort(
    (a, b) => b.run_metadata.timestamp.localeCompare(a.run_metadata.timestamp),
  );
}

/** Check if a value is a flat numeric score (not a nested object) */
export function isNumericScore(value: unknown): value is number {
  return typeof value === 'number' && !isNaN(value);
}
