---
inclusion: auto
---

# Eval Run Capture

When the user shares eval run output containing `=== EVALUATION REPORT ===`, immediately do the following:

1. Append a new entry to `docs/project-updates/eval-run-log.md` with:
   - Run number (increment from the last entry)
   - Timestamp from the report
   - Config: dataset version, prompt versions, judge yes/no, architecture
   - Key metrics: pass rate, per-category accuracy, IntentPreservation, CriteriaMethodAlignment, Verification-Builder-centric score
   - What changed from the previous run (exactly one variable per Decision 50)
   - Insight: what the numbers tell us
   - Next: what to do based on the insight

2. If the run is a different architecture than the previous run, also update `docs/project-updates/architecture-insights.md`:
   - Update the metrics under the relevant architecture section
   - Add new observations to Cross-Architecture Observations if the comparison reveals something new
   - Update Prompt Needs if the data suggests new prompt improvements

3. Do NOT use "VB" as an abbreviation in prose. Always write "Verification Builder" in full. Exception: existing code keys like `vb_centric_score` are fine.
