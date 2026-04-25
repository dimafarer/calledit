# Requirements Document

## Introduction

Update the Continuous Eval dashboard to visually distinguish between different types of inconclusive cases using a 4-color scheme based on system health. Currently, the dashboard uses a binary green/red color scheme (resolved vs. inconclusive). Decision 161 established that inconclusive cases have fundamentally different root causes — some are expected (future-dated predictions, personal/subjective predictions) and some signal real system problems (immediate-mode predictions that should have resolved). The 4-color scheme surfaces this distinction so the developer can immediately see which inconclusive cases need investigation vs. which are working as designed.

## Glossary

- **Dashboard**: The React-based Continuous Eval tab at `/eval` in the `frontend-v4` app, rendering scatter plots, case tables, and resolution rate charts from DynamoDB eval reports.
- **Case_Result**: A single prediction's evaluation outcome stored in the eval report, containing fields: `status`, `verdict`, `verifiability_score`, `score_tier`, `verification_mode`, `expected_verdict`, `verification_date`.
- **Categorizer**: A pure function that classifies a Case_Result into one of four Inconclusive_Category values based on its fields.
- **Inconclusive_Category**: One of four mutually exclusive categories: `resolved`, `future_dated`, `personal_subjective`, `should_have_resolved`, or `uncategorized` (fallback for inconclusive cases that don't match any specific subcategory).
- **CalibrationScatter**: The Recharts scatter plot component (`CalibrationScatter.tsx`) that plots verifiability_score (x) vs. verification outcome (y) with colored dots.
- **CaseTable**: The data-driven table component (`CaseTable.tsx`) that renders case rows with status and verdict columns for the continuous agent type.
- **ResolutionRateChart**: The Recharts line chart component (`ResolutionRateChart.tsx`) that plots resolution rate and stale inconclusive rate over verification passes.
- **Color_Scheme**: The 4-color mapping: green (`#22c55e`) = resolved, amber (`#f59e0b`) = future-dated, red (`#ef4444`) = personal/subjective, orange (`#f97316`) = should-have-resolved.

## Requirements

### Requirement 1: Inconclusive Category Classification

**User Story:** As a developer reviewing continuous eval results, I want each case automatically classified into one of four health categories, so that I can immediately understand why a case is inconclusive without manually inspecting its fields.

#### Acceptance Criteria

1. WHEN a Case_Result has `status === "resolved"`, THE Categorizer SHALL return `resolved`.
2. WHEN a Case_Result has `status === "inconclusive"` AND `verification_mode` is `"at_date"` or `"before_date"` AND `expected_verdict` is null, THE Categorizer SHALL return `future_dated`.
3. WHEN a Case_Result has `status === "inconclusive"` AND `verifiability_score` is less than 0.4, THE Categorizer SHALL return `personal_subjective`.
4. WHEN a Case_Result has `status === "inconclusive"` AND `verification_mode === "immediate"` AND `verifiability_score` is greater than or equal to 0.7, THE Categorizer SHALL return `should_have_resolved`.
5. WHEN a Case_Result has `status === "inconclusive"` AND does not match criteria 2, 3, or 4, THE Categorizer SHALL return `uncategorized`.
6. WHEN a Case_Result has `status` that is neither `"resolved"` nor `"inconclusive"` (e.g., `"pending"` or `"error"`), THE Categorizer SHALL return `uncategorized`.
7. THE Categorizer SHALL be a pure function with no side effects, accepting a single Case_Result record and returning an Inconclusive_Category string.
8. THE Categorizer SHALL evaluate classification rules in priority order: resolved first, then future_dated, then personal_subjective, then should_have_resolved, then uncategorized as fallback.

### Requirement 2: Color Mapping

**User Story:** As a developer, I want each inconclusive category mapped to a distinct color, so that the visual encoding is consistent across all dashboard components.

#### Acceptance Criteria

1. THE Color_Scheme SHALL map `resolved` to green (`#22c55e`).
2. THE Color_Scheme SHALL map `future_dated` to amber (`#f59e0b`).
3. THE Color_Scheme SHALL map `personal_subjective` to red (`#ef4444`).
4. THE Color_Scheme SHALL map `should_have_resolved` to orange (`#f97316`).
5. THE Color_Scheme SHALL map `uncategorized` to grey (`#64748b`).
6. THE Color_Scheme SHALL be defined as a single constant mapping object in the shared utilities module (`utils.ts`), reused by all dashboard components.

### Requirement 3: Scatter Plot 4-Color Dots

**User Story:** As a developer viewing the calibration scatter plot, I want dot colors to reflect the 4-category health scheme instead of the binary calibration-correct scheme, so that I can visually identify clusters of future-dated, personal/subjective, and should-have-resolved cases.

#### Acceptance Criteria

1. WHEN the CalibrationScatter renders for the `continuous` agent type, THE CalibrationScatter SHALL color each dot according to the Color_Scheme based on the case's Inconclusive_Category.
2. WHEN a user hovers over a dot in the CalibrationScatter, THE tooltip SHALL display the case's Inconclusive_Category label alongside the existing case ID, score, and verdict information.
3. THE CalibrationScatter SHALL display a legend below the subtitle text showing all four colors with their category labels.
4. WHEN the CalibrationScatter renders for non-continuous agent types (calibration, unified), THE CalibrationScatter SHALL retain the existing binary green/red calibration-correct color scheme.

### Requirement 4: Case Table Status and Verdict Colors

**User Story:** As a developer scanning the case table, I want the status and verdict columns to use the 4-color scheme, so that I can quickly identify which inconclusive cases are expected vs. problematic without expanding each row.

#### Acceptance Criteria

1. WHEN the CaseTable renders a continuous case row, THE CaseTable SHALL color the verdict cell text according to the Color_Scheme based on the case's Inconclusive_Category.
2. WHEN the CaseTable renders a continuous case row, THE CaseTable SHALL color the status cell text according to the Color_Scheme based on the case's Inconclusive_Category.
3. THE CaseTable SHALL replace the existing `getContinuousVerdictColor` call with the new Categorizer-based color lookup for continuous agent type rows.

### Requirement 5: Replace Existing getContinuousVerdictColor

**User Story:** As a developer maintaining the codebase, I want the old `getContinuousVerdictColor` function replaced by the new Categorizer and Color_Scheme, so that there is a single source of truth for continuous case coloring.

#### Acceptance Criteria

1. THE Dashboard SHALL remove the existing `getContinuousVerdictColor` function from `utils.ts`.
2. THE Dashboard SHALL export a new `getInconclusiveCategory` function from `utils.ts` that implements the Categorizer logic.
3. THE Dashboard SHALL export a new `getCategoryColor` function from `utils.ts` that maps an Inconclusive_Category to its hex color string using the Color_Scheme constant.
4. WHEN any component previously called `getContinuousVerdictColor`, THE component SHALL call `getCategoryColor(getInconclusiveCategory(caseResult))` instead.

### Requirement 6: Resolution Rate Chart Legend Consideration

**User Story:** As a developer viewing the resolution rate trend, I want the chart to remain readable and consistent with the new color scheme where applicable.

#### Acceptance Criteria

1. THE ResolutionRateChart SHALL retain its existing green line for resolution rate and red line for stale inconclusive rate, as these are aggregate metrics not per-case categories.
2. IF the ResolutionRateChart's "Stale Inconclusive" line semantically aligns with the `should_have_resolved` category, THE ResolutionRateChart SHALL update the stale inconclusive line color from red (`#ef4444`) to orange (`#f97316`) to match the Color_Scheme.
