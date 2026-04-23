"""Continuous eval state management.

Manages the persistent state file (eval/continuous_state.json) that tracks
case lifecycle across verification passes. Pure data operations — file I/O
only at boundaries (load/save).
"""

import json
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Literal

logger = logging.getLogger(__name__)


@dataclass
class VerdictEntry:
    """Single verdict from one verification pass."""
    pass_number: int
    timestamp: str
    verdict: str
    confidence: float | None = None


@dataclass
class CaseState:
    """Per-case lifecycle state."""
    case_id: str
    prediction_id: str | None = None
    status: Literal["pending", "inconclusive", "resolved", "error"] = "pending"
    verdict: str | None = None
    confidence: float | None = None
    evidence: list[dict] | None = None
    reasoning: str | None = None
    creation_error: str | None = None
    verification_error: str | None = None
    creation_duration: float = 0.0
    verification_date: str | None = None
    resolved_on_pass: int | None = None
    verifiability_score: float | None = None
    score_tier: str | None = None
    verdict_history: list[VerdictEntry] = field(default_factory=list)


@dataclass
class ContinuousState:
    """Top-level state persisted to continuous_state.json."""
    pass_number: int = 0
    cases: dict[str, CaseState] = field(default_factory=dict)
    pass_timestamps: list[str] = field(default_factory=list)
    created_at: str = ""
    eval_table: str = "calledit-v4-eval"

    @classmethod
    def fresh(cls, eval_table: str = "calledit-v4-eval") -> "ContinuousState":
        """Create empty state for a new continuous run."""
        return cls(
            pass_number=0,
            cases={},
            pass_timestamps=[],
            created_at=datetime.now(timezone.utc).isoformat(),
            eval_table=eval_table,
        )

    @classmethod
    def load(cls, path: str) -> "ContinuousState":
        """Load state from JSON file. Returns fresh state if file missing or corrupt."""
        try:
            with open(path, "r") as f:
                data = json.load(f)
        except FileNotFoundError:
            logger.info(f"No state file at {path} — starting fresh")
            return cls.fresh()
        except json.JSONDecodeError as e:
            logger.warning(f"Corrupt state file at {path}: {e} — starting fresh")
            return cls.fresh()

        cases = {}
        for case_id, case_data in data.get("cases", {}).items():
            verdict_history = [
                VerdictEntry(**vh) for vh in case_data.pop("verdict_history", [])
            ]
            cases[case_id] = CaseState(
                **{k: v for k, v in case_data.items() if k != "verdict_history"},
                verdict_history=verdict_history,
            )

        return cls(
            pass_number=data.get("pass_number", 0),
            cases=cases,
            pass_timestamps=data.get("pass_timestamps", []),
            created_at=data.get("created_at", ""),
            eval_table=data.get("eval_table", "calledit-v4-eval"),
        )

    def save(self, path: str) -> None:
        """Serialize state to JSON file."""
        data = {
            "pass_number": self.pass_number,
            "created_at": self.created_at,
            "eval_table": self.eval_table,
            "pass_timestamps": self.pass_timestamps,
            "cases": {
                case_id: asdict(case_state)
                for case_id, case_state in self.cases.items()
            },
        }
        try:
            with open(path, "w") as f:
                json.dump(data, f, indent=2, default=str)
        except OSError as e:
            logger.error(f"Failed to save state to {path}: {e}")

    def get_eligible_for_verification(self, reverify_resolved: bool = False) -> list[CaseState]:
        """Return cases eligible for verification this pass.

        Eligible: pending or inconclusive with a prediction_id.
        If reverify_resolved=True, also include resolved cases.
        Error cases with no prediction_id are always excluded.
        """
        eligible = []
        for case in self.cases.values():
            if case.prediction_id is None:
                continue
            if case.status in ("pending", "inconclusive"):
                eligible.append(case)
            elif case.status == "resolved" and reverify_resolved:
                eligible.append(case)
        return eligible

    def update_case_verdict(
        self,
        case_id: str,
        verdict: str | None,
        confidence: float | None,
        pass_number: int,
    ) -> None:
        """Update a case's status based on verification result.

        - confirmed/refuted → status=resolved, set resolved_on_pass (first time only)
        - inconclusive → status=inconclusive
        - None (error) → preserve previous status and verdict
        - Always appends to verdict_history (except None)
        """
        case = self.cases.get(case_id)
        if case is None:
            logger.warning(f"update_case_verdict: unknown case_id {case_id}")
            return

        if verdict is None:
            # Error — preserve previous state
            return

        # Append to history
        case.verdict_history.append(VerdictEntry(
            pass_number=pass_number,
            timestamp=datetime.now(timezone.utc).isoformat(),
            verdict=verdict,
            confidence=confidence,
        ))

        if verdict in ("confirmed", "refuted"):
            case.status = "resolved"
            case.verdict = verdict
            case.confidence = confidence
            if case.resolved_on_pass is None:
                case.resolved_on_pass = pass_number
        elif verdict == "inconclusive":
            case.status = "inconclusive"
            case.verdict = verdict
            case.confidence = confidence
