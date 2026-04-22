"""Task function — two-agent pipeline callable for Strands Evals SDK.

Chains creation agent → verification wait → verification agent for each Case.
Passed to Experiment.run_evaluations() as the task function.

Usage:
    task_fn = TaskFunctionFactory(creation_backend, verification_backend, eval_table)
    experiment = Experiment(cases=cases, evaluators=evaluators)
    reports = experiment.run_evaluations(task_fn)
"""

import logging
import time
from datetime import datetime, timezone
from typing import Optional

from strands_evals import Case

logger = logging.getLogger(__name__)


def compute_wait_seconds(
    bundle: dict,
    verification_mode: str = "immediate",
    now: Optional[datetime] = None,
) -> float:
    """Compute how long to wait before verification.

    Args:
        bundle: Creation bundle with parsed_claim.verification_date.
        verification_mode: The prediction's verification mode.
        now: Current time (defaults to UTC now, injectable for testing).

    Returns:
        Wait time in seconds. 0 for immediate/recurring or past dates.
        max(0, (vdate - now).total_seconds() + 30) capped at 300s.
    """
    if verification_mode in ("immediate", "recurring"):
        return 0.0

    if now is None:
        now = datetime.now(timezone.utc)

    raw = bundle.get("raw_bundle", bundle)
    vdate_str = (
        raw.get("parsed_claim", {}).get("verification_date")
        or raw.get("verification_date")
    )
    if not vdate_str:
        return 0.0

    try:
        vdate = datetime.fromisoformat(str(vdate_str).replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        logger.warning("Unparseable verification_date: %s", vdate_str)
        return 0.0

    if vdate <= now:
        return 0.0

    wait = (vdate - now).total_seconds() + 30  # 30s buffer
    return min(wait, 300.0)  # Cap at 5 minutes


class TaskFunctionFactory:
    """Creates a task function with pre-configured backends.

    The __call__ method is passed to Experiment.run_evaluations().
    """

    def __init__(
        self,
        creation_backend,
        verification_backend,
        eval_table_name: str,
        resume_ids: Optional[set] = None,
        token_refresher: Optional[callable] = None,
    ):
        self.creation_backend = creation_backend
        self.verification_backend = verification_backend
        self.eval_table_name = eval_table_name
        self.resume_ids = resume_ids or set()
        self.token_refresher = token_refresher
        self._token_time = time.time()
        self._token_ttl = 3000  # Refresh after 50 min (Cognito tokens last 60 min)

    def _maybe_refresh_token(self):
        """Refresh the Cognito token if it's about to expire."""
        if self.token_refresher and (time.time() - self._token_time) > self._token_ttl:
            logger.info("Refreshing Cognito token (%.0fs since last refresh)",
                        time.time() - self._token_time)
            try:
                new_token = self.token_refresher()
                self.creation_backend.set_token(new_token)
                self._token_time = time.time()
                logger.info("Token refreshed successfully")
            except Exception as e:
                logger.error("Token refresh failed: %s", e)

    def __call__(self, case: Case) -> dict:
        """Execute creation → wait → verification pipeline for one Case.

        Returns dict wrapped with "output" key for SDK compatibility.
        The SDK extracts actual_output = return_value["output"].
        """
        result = {
            "creation_bundle": None,
            "verification_result": None,
            "creation_error": None,
            "verification_error": None,
            "prediction_id": None,
            "creation_duration": 0.0,
            "verification_duration": 0.0,
        }

        case_id = case.name or "unknown"
        mode = (case.metadata or {}).get("verification_mode", "immediate")

        # --- Creation ---
        self._maybe_refresh_token()
        start = time.time()
        try:
            bundle = self.creation_backend.invoke(
                prediction_text=case.input,
                case_id=case_id,
            )
            result["creation_bundle"] = bundle
            result["prediction_id"] = bundle.get("prediction_id")
            logger.info(
                "Case %s: creation OK (prediction_id=%s)",
                case_id, result["prediction_id"],
            )
        except Exception as e:
            result["creation_error"] = str(e)
            logger.error("Case %s: creation failed: %s", case_id, e)
            result["creation_duration"] = time.time() - start
            return {"output": result}
        result["creation_duration"] = time.time() - start

        # --- Wait ---
        wait = compute_wait_seconds(bundle, mode)
        if wait > 0:
            logger.info("Case %s: waiting %.0fs for verification date", case_id, wait)
            time.sleep(wait)

        # --- Verification ---
        prediction_id = result["prediction_id"]
        if not prediction_id:
            result["verification_error"] = "No prediction_id from creation"
            return {"output": result}

        start = time.time()
        try:
            vresult = self.verification_backend.invoke(
                prediction_id=prediction_id,
                table_name=self.eval_table_name,
                case_id=case_id,
            )
            result["verification_result"] = vresult
            logger.info(
                "Case %s: verification OK (verdict=%s)",
                case_id, vresult.get("verdict"),
            )
        except Exception as e:
            result["verification_error"] = str(e)
            logger.error("Case %s: verification failed: %s", case_id, e)
        result["verification_duration"] = time.time() - start

        return {"output": result}
