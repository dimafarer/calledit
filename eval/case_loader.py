"""Case loader — golden dataset to Strands Evals SDK Case objects.

Loads golden dataset predictions (static + optional dynamic) and constructs
Strands Evals SDK Case objects for use with Experiment.run_evaluations().

Usage:
    from eval.case_loader import load_cases

    cases = load_cases("eval/golden_dataset.json")
    cases = load_cases("eval/golden_dataset.json", "eval/dynamic_golden_dataset.json")
    cases = load_cases("eval/golden_dataset.json", tier="smoke")
    cases = load_cases("eval/golden_dataset.json", case_id="base-002")
"""

import logging
import sys
from typing import Optional

from strands_evals import Case

from eval.dataset_merger import load_and_merge

logger = logging.getLogger(__name__)


def load_cases(
    static_path: str,
    dynamic_path: Optional[str] = None,
    tier: Optional[str] = None,
    case_id: Optional[str] = None,
) -> list[Case]:
    """Load golden dataset, merge, filter, and construct Case objects.

    Args:
        static_path: Path to the static golden dataset JSON.
        dynamic_path: Optional path to the dynamic golden dataset JSON.
        tier: If "smoke", filter to smoke_test=True cases only.
        case_id: If provided, filter to a single case by prediction id.

    Returns:
        List of Case objects ready for Experiment.run_evaluations().
    """
    dataset = load_and_merge(static_path, dynamic_path)
    predictions = dataset.get("base_predictions", [])

    cases = [_prediction_to_case(p) for p in predictions]

    cases = _filter_cases(cases, tier=tier, case_id=case_id)

    if not cases:
        print("Error: no qualifying cases after filtering", file=sys.stderr)
        sys.exit(1)

    logger.info("Loaded %d cases (tier=%s, case_id=%s)", len(cases), tier, case_id)
    return cases


def _prediction_to_case(prediction: dict) -> Case:
    """Convert a single golden dataset prediction dict to a Case object."""
    expected_outcome = prediction.get("expected_verification_outcome")

    return Case(
        name=prediction.get("id", "unknown"),
        input=prediction.get("prediction_text", ""),
        expected_output=expected_outcome,
        session_id=prediction.get("id", "unknown"),
        metadata={
            "id": prediction.get("id"),
            "difficulty": prediction.get("difficulty"),
            "verification_mode": prediction.get("verification_mode"),
            "smoke_test": prediction.get("smoke_test", False),
            "ground_truth": prediction.get("ground_truth", {}),
            "expected_verifiability_score_range": prediction.get(
                "expected_verifiability_score_range"
            ),
            "qualifying": expected_outcome is not None,
            "evaluation_rubric": prediction.get("evaluation_rubric"),
            "verification_readiness": prediction.get("verification_readiness"),
        },
    )


def _filter_cases(
    cases: list[Case],
    tier: Optional[str] = None,
    case_id: Optional[str] = None,
) -> list[Case]:
    """Filter cases by tier or specific case id.

    Args:
        cases: Full list of Case objects.
        tier: If "smoke", keep only smoke_test=True cases.
        case_id: If provided, keep only the case with this id.

    Returns:
        Filtered list of Case objects.
    """
    if case_id:
        filtered = [c for c in cases if c.name == case_id]
        if not filtered:
            logger.warning("Case '%s' not found in dataset", case_id)
        return filtered

    if tier == "smoke":
        return [c for c in cases if c.metadata.get("smoke_test")]

    return cases
