"""
Online Evaluation Sampling

Provides deterministic session sampling for continuous production evaluation.
Sampling is based on a hash of the session/connection ID, making it
reproducible and evenly distributed without storing state.

USAGE IN PRODUCTION:
    from online_eval import should_sample_session

    if should_sample_session(connection_id, rate=0.1):
        # Submit trace to AgentCore for evaluation
        pass

The default rate is 10% (0.1). Configurable via ONLINE_EVAL_SAMPLE_RATE env var.
"""

import hashlib
import logging
import os

logger = logging.getLogger(__name__)


def should_sample_session(session_id: str, rate: float = None) -> bool:
    """
    Determine if a session should be sampled for online evaluation.

    Uses a deterministic hash of the session ID so the same session always
    gets the same sampling decision. This avoids needing external state
    and ensures even distribution across sessions.

    Args:
        session_id: WebSocket connection ID or session identifier.
        rate: Sampling rate between 0.0 and 1.0 (default from env or 0.1).

    Returns:
        True if the session should be evaluated, False otherwise.
    """
    if rate is None:
        rate = float(os.environ.get("ONLINE_EVAL_SAMPLE_RATE", "0.1"))

    rate = max(0.0, min(1.0, rate))

    if rate == 0.0:
        return False
    if rate == 1.0:
        return True

    # Deterministic hash → float in [0, 1)
    hash_bytes = hashlib.sha256(session_id.encode("utf-8")).digest()
    hash_int = int.from_bytes(hash_bytes[:8], byteorder="big")
    hash_float = hash_int / (2**64)

    return hash_float < rate
