"""Continuous eval metrics.

Computes continuous-specific metrics: resolution rate, stale inconclusive rate,
resolution speed by V-score tier. All functions are pure — no I/O.
"""

from __future__ import annotations

import statistics
from datetime import datetime, timezone
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from eval.continuous_state import ContinuousState


def compute_resolution_rate(state: ContinuousState) -> float:
    """Fraction of verified cases that have resolved.

    resolved_count / verified_at_least_once_count.
    Returns 0.0 when no cases have been verified.
    """
    verified = [c for c in state.cases.values() if len(c.verdict_history) >= 1]
    if not verified:
        return 0.0
    resolved = [c for c in verified if c.status == "resolved"]
    return len(resolved) / len(verified)


def compute_stale_inconclusive_rate(
    state: ContinuousState,
    now: datetime | None = None,
) -> float:
    """Fraction of past-due cases that are still inconclusive.

    (inconclusive AND verification_date < now) / (verification_date < now).
    Excludes cases with future or null verification dates.
    Returns 0.0 when no cases have past verification dates.
    """
    if now is None:
        now = datetime.now(timezone.utc)

    past_due = []
    for case in state.cases.values():
        if case.verification_date is None:
            continue
        try:
            vdate = datetime.fromisoformat(case.verification_date)
            if vdate.tzinfo is None:
                vdate = vdate.replace(tzinfo=timezone.utc)
            if vdate < now:
                past_due.append(case)
        except (ValueError, TypeError):
            continue

    if not past_due:
        return 0.0

    stale = [c for c in past_due if c.verdict == "inconclusive"]
    return len(stale) / len(past_due)


def compute_resolution_speed_by_tier(
    state: ContinuousState,
) -> dict[str, float | None]:
    """Median pass number at which each V-score tier first resolved.

    Tiers: high (>= 0.7), moderate (0.4–0.7), low (< 0.4).
    Returns null for tiers with fewer than 2 resolved cases.
    """
    tiers: dict[str, list[int]] = {"high": [], "moderate": [], "low": []}

    for case in state.cases.values():
        if case.status != "resolved" or case.resolved_on_pass is None:
            continue
        if case.verifiability_score is None:
            continue

        score = case.verifiability_score
        if score >= 0.7:
            tiers["high"].append(case.resolved_on_pass)
        elif score >= 0.4:
            tiers["moderate"].append(case.resolved_on_pass)
        else:
            tiers["low"].append(case.resolved_on_pass)

    result: dict[str, float | None] = {}
    for tier_name, passes in tiers.items():
        if len(passes) < 2:
            result[tier_name] = None
        else:
            result[tier_name] = statistics.median(passes)

    return result


def compute_continuous_calibration(
    state: ContinuousState,
    task_outputs: list[dict] | None = None,
) -> dict:
    """Full calibration dict for continuous reports.

    Combines resolution_rate, stale_inconclusive_rate, resolution_speed_by_tier,
    and verdict distribution.
    """
    now = datetime.now(timezone.utc)

    # Verdict distribution
    distribution: dict[str, int] = {
        "confirmed": 0, "refuted": 0, "inconclusive": 0, "error": 0, "pending": 0,
    }
    for case in state.cases.values():
        if case.status == "error":
            distribution["error"] += 1
        elif case.status == "pending":
            distribution["pending"] += 1
        elif case.verdict in distribution:
            distribution[case.verdict] += 1

    return {
        "resolution_rate": compute_resolution_rate(state),
        "stale_inconclusive_rate": compute_stale_inconclusive_rate(state, now),
        "resolution_speed_by_tier": compute_resolution_speed_by_tier(state),
        "verdict_distribution": distribution,
    }
