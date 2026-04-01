# Requirements Document: Strands Evals Dashboard Adaptation (Spec B)

## Introduction

After Spec A (`strands-evals-migration`) migrates the Python eval pipeline to the Strands Evals SDK, the React dashboard and report store read interface need to be updated to consume the new report format. This is Spec B — the cross-stack integration work (Python → DDB → Lambda → React).

**Prerequisite:** Spec A must be complete. The new pipeline must be writing reports to DDB before this spec starts.

## Requirements

### Requirement 1: Report Store Read Adaptation

**User Story:** As a dashboard developer, I want the report store's read interface to parse SDK-format reports, so that the dashboard Lambda can serve the new data shape.

#### Acceptance Criteria

1. THE `list_reports()` function SHALL return report summaries from both old-format and new SDK-format reports in the `calledit-v4-eval-reports` DDB table.
2. THE `get_report()` function SHALL parse SDK-format reports and return them with `creation_scores`, `verification_scores`, `calibration_scores`, and `case_results` top-level keys.
3. THE `get_report()` function SHALL handle the item split pattern (main item + `{timestamp}#CASES` item) for both old and new report formats.

### Requirement 2: Dashboard TypeScript Interfaces

**User Story:** As a dashboard developer, I want TypeScript interfaces updated for the SDK report schema, so that the dashboard components can type-check against the new data shape.

#### Acceptance Criteria

1. THE Dashboard TypeScript interfaces SHALL include types for `creation_scores`, `verification_scores`, `calibration_scores`, and `case_results` matching the SDK report format.
2. THE Dashboard SHALL maintain backward compatibility with historical reports already in DDB by using optional fields or union types where the old and new formats differ.

### Requirement 3: Dashboard Component Updates

**User Story:** As a user, I want the eval dashboard to correctly display results from the new SDK pipeline, so that I can visualize eval results after the migration.

#### Acceptance Criteria

1. THE Unified Pipeline tab SHALL render the calibration scatter plot, three-column score grid, phase timing breakdown, and per-case results table from SDK-format reports.
2. THE Dashboard SHALL render per-evaluator scores with pass/fail indicators for both creation and verification evaluator sets.
3. THE Dashboard SHALL render calibration metrics including calibration_accuracy, mean_absolute_error, high_score_confirmation_rate, low_score_failure_rate, and verdict_distribution.
4. THE Dashboard SHALL handle reports where some fields are missing (backward compatibility with older reports).
