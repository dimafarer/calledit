# Bugfix Requirements Document

## Introduction

Three bugs in the Continuous Eval dashboard prevent correct visualization and tracking of verification results. Bug 1 makes chart lines invisible when values sit at axis boundaries. Bug 2 causes inconclusive cases to be missing from the scatter plot because their `actual_verdict` is not populated in the backend task outputs. Bug 3 causes all continuous eval reports to be labeled "Pass 1" because pass numbering resets on each CLI invocation instead of continuing from the last saved state.

## Bug Analysis

### Current Behavior (Defect)

1.1 WHEN `resolution_rate` equals 1.0 THEN the green line in ResolutionRateChart is invisible because it sits exactly on the top border of the Y-axis domain `[0, 1]` and blends with the chart grid line

1.2 WHEN `stale_inconclusive_rate` equals 0.0 THEN the red line in ResolutionRateChart is invisible because it sits exactly on the bottom border of the Y-axis domain `[0, 1]` and blends with the chart grid line

1.3 WHEN a case has `cs.verdict = "inconclusive"` and `cs.status = "inconclusive"` THEN the system does not construct a `verification_result` dict for that case because the condition `cs.status == "resolved"` excludes it, resulting in `actual_verdict` being `None` in the case results

1.4 WHEN `actual_verdict` is `None` for inconclusive cases THEN the CalibrationScatter chart filters them out (it requires both `verifiability_score` and `actual_verdict` to be non-null), so inconclusive cases never appear on the scatter plot

1.5 WHEN the continuous eval runner is invoked with `--once --resume` or `--verify-only` THEN `pass_num` starts at 0 in the `run()` method and increments to 1, regardless of how many passes were previously completed, causing all reports to be labeled "Pass 1"

### Expected Behavior (Correct)

2.1 WHEN `resolution_rate` equals 1.0 THEN the system SHALL display the green line with visible padding above it by using a Y-axis domain of `[-0.05, 1.05]` and a dot radius large enough to be clearly visible at axis boundaries

2.2 WHEN `stale_inconclusive_rate` equals 0.0 THEN the system SHALL display the red line with visible padding below it by using a Y-axis domain of `[-0.05, 1.05]` and a dot radius large enough to be clearly visible at axis boundaries

2.3 WHEN a case has `cs.verdict = "inconclusive"` and `cs.status = "inconclusive"` THEN the system SHALL construct a `verification_result` dict containing the verdict, confidence, evidence, and reasoning, so that `extract_case_results()` populates `actual_verdict` with `"inconclusive"`

2.4 WHEN inconclusive cases have a populated `actual_verdict` THEN the CalibrationScatter chart SHALL display them as data points on the scatter plot at the `y = 0.5` (inconclusive) position

2.5 WHEN the continuous eval runner is invoked with `--resume` THEN the system SHALL start `pass_num` from `self.state.pass_number` (the last completed pass number) so that subsequent passes are numbered sequentially (e.g., if the last pass was 3, the next pass starts at 4)

### Unchanged Behavior (Regression Prevention)

3.1 WHEN `resolution_rate` is between 0.05 and 0.95 (not at axis boundaries) THEN the system SHALL CONTINUE TO display the green line clearly within the chart area

3.2 WHEN `stale_inconclusive_rate` is between 0.05 and 0.95 (not at axis boundaries) THEN the system SHALL CONTINUE TO display the red line clearly within the chart area

3.3 WHEN a case has `cs.status = "resolved"` and `cs.verdict` is `"confirmed"` or `"refuted"` THEN the system SHALL CONTINUE TO construct a `verification_result` dict and populate `actual_verdict` correctly

3.4 WHEN a case has no verdict (e.g., `cs.verdict` is `None` or status is `"pending"` or `"error"`) THEN the system SHALL CONTINUE TO set `verification_result` to `None` and exclude the case from the scatter plot

3.5 WHEN the continuous eval runner is invoked without `--resume` (fresh state) THEN the system SHALL CONTINUE TO start pass numbering from 1

3.6 WHEN the continuous eval runner runs in non-continuous batched mode THEN the system SHALL CONTINUE TO function identically with no changes to pass numbering or verification result construction
