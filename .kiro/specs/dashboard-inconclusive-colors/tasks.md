# Implementation Plan: Dashboard Inconclusive Colors

## Overview

Replace the binary green/red color scheme in the Continuous Eval dashboard with a 4-color scheme that visually distinguishes different root causes of inconclusive cases. All changes are scoped to `frontend-v4/src/pages/EvalDashboard/`. The categorizer and color mapping live in `utils.ts` and are consumed by `CalibrationScatter`, `CaseTable`, and `ResolutionRateChart`.

## Tasks

- [ ] 1. Add categorizer, color mapping, and labels to utils.ts
  - [ ] 1.1 Add `InconclusiveCategory` type, `CATEGORY_COLORS` constant, `CATEGORY_LABELS` constant, `getInconclusiveCategory` function, and `getCategoryColor` function to `utils.ts`
    - Define the `InconclusiveCategory` string literal union type
    - Define `CATEGORY_COLORS` record mapping each category to its hex color
    - Define `CATEGORY_LABELS` record mapping each category to its human-readable label
    - Implement `getInconclusiveCategory(caseResult: Record<string, unknown>): InconclusiveCategory` with priority-ordered rules: resolved → future_dated → personal_subjective → should_have_resolved → uncategorized
    - Implement `getCategoryColor(category: InconclusiveCategory): string` that looks up the color from `CATEGORY_COLORS`, defaulting to uncategorized grey for unknown input
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 5.2, 5.3_

  - [ ] 1.2 Remove `getContinuousVerdictColor` from `utils.ts`
    - Delete the `getContinuousVerdictColor` function
    - _Requirements: 5.1_

  - [ ]* 1.3 Write property tests for `getInconclusiveCategory` using fast-check
    - **Property 1: Resolved status always returns resolved**
    - **Validates: Requirements 1.1, 1.8**

  - [ ]* 1.4 Write property test for future-dated classification with priority
    - **Property 2: Future-dated classification with priority**
    - **Validates: Requirements 1.2, 1.8**

  - [ ]* 1.5 Write property test for personal/subjective classification
    - **Property 3: Personal/subjective classification**
    - **Validates: Requirements 1.3**

  - [ ]* 1.6 Write property test for should-have-resolved classification
    - **Property 4: Should-have-resolved classification**
    - **Validates: Requirements 1.4**

  - [ ]* 1.7 Write property test for uncategorized fallback
    - **Property 5: Uncategorized fallback**
    - **Validates: Requirements 1.5, 1.6**

  - [ ]* 1.8 Write property test for exhaustive and deterministic categorization
    - **Property 6: Exhaustive and deterministic categorization**
    - **Validates: Requirements 1.7, 2.1, 2.2, 2.3, 2.4, 2.5**

  - [ ]* 1.9 Write unit tests for color and label mappings
    - Verify each of the 5 categories maps to the correct hex color
    - Verify each category has the correct human-readable label
    - Verify `getContinuousVerdictColor` is no longer exported
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 5.1_

- [ ] 2. Checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 3. Update CaseTable to use 4-color scheme for continuous cases
  - [ ] 3.1 Replace `getContinuousVerdictColor` usage in `CaseTable.tsx`
    - Import `getInconclusiveCategory`, `getCategoryColor` from `../utils`
    - Remove `getContinuousVerdictColor` from the import statement
    - For `agentType === 'continuous'` rows, replace the verdict cell color logic with `getCategoryColor(getInconclusiveCategory(raw))`
    - For `agentType === 'continuous'` rows, replace the status cell color logic with `getCategoryColor(getInconclusiveCategory(raw))`
    - _Requirements: 4.1, 4.2, 4.3, 5.4_

- [ ] 4. Update CalibrationScatter with agentType prop and 4-color dots
  - [ ] 4.1 Add `agentType` prop to `CalibrationScatter` and pass it from `AgentTab`
    - Add `agentType: AgentType` to the `Props` interface in `CalibrationScatter.tsx`
    - Import `AgentType` from `../types`
    - In `AgentTab.tsx`, pass `agentType={agentType}` to the `<CalibrationScatter>` component
    - _Requirements: 3.4_

  - [ ] 4.2 Implement 4-color dot rendering for continuous agent type
    - Import `getInconclusiveCategory`, `getCategoryColor`, `CATEGORY_COLORS`, `CATEGORY_LABELS` from `../utils`
    - When `agentType === 'continuous'`: compute category via `getInconclusiveCategory` for each data point, color dots via `getCategoryColor`
    - When `agentType !== 'continuous'`: retain existing binary green/red calibration-correct coloring
    - _Requirements: 3.1, 3.4_

  - [ ] 4.3 Add category to tooltip and legend for continuous mode
    - When `agentType === 'continuous'`: display the `InconclusiveCategory` label in the tooltip alongside case ID, score, and verdict
    - Render a legend below the subtitle text showing all category colors with their labels
    - _Requirements: 3.2, 3.3_

- [ ] 5. Update ResolutionRateChart stale inconclusive line color
  - [ ] 5.1 Change the "Stale Inconclusive" line stroke from `#ef4444` (red) to `#f97316` (orange) in `ResolutionRateChart.tsx`
    - _Requirements: 6.2_

- [ ] 6. Final checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Property tests validate the 6 correctness properties from the design using fast-check
- The categorizer operates on `Record<string, unknown>` to handle raw API JSON without type changes
- Only the `continuous` agent type uses the new 4-color scheme; calibration/unified retain binary coloring
