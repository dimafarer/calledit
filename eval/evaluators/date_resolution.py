"""Tier 1: Date Resolution — checks verification_date is valid ISO 8601."""

from datetime import datetime


def evaluate(bundle: dict) -> dict:
    """Check verification_date is a valid ISO 8601 datetime string.

    Returns: {"score": 1.0|0.0, "pass": bool, "reason": str}
    """
    claim = bundle.get("parsed_claim", {})
    date_str = claim.get("verification_date")

    if not date_str or not isinstance(date_str, str):
        return {
            "score": 0.0,
            "pass": False,
            "reason": f"verification_date missing or not a string: {date_str!r}",
        }

    # Try multiple ISO 8601 formats
    for fmt in (
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%S.%fZ",
        "%Y-%m-%dT%H:%M:%S.%f%z",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d",
    ):
        try:
            datetime.strptime(date_str.replace("+00:00", "Z").rstrip("Z") + "Z"
                              if "Z" not in date_str and "+" not in date_str
                              else date_str, fmt)
            return {
                "score": 1.0,
                "pass": True,
                "reason": f"Valid ISO 8601: {date_str}",
            }
        except ValueError:
            continue

    # Fallback: try fromisoformat (Python 3.11+)
    try:
        datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        return {
            "score": 1.0,
            "pass": True,
            "reason": f"Valid ISO 8601: {date_str}",
        }
    except (ValueError, TypeError):
        pass

    return {
        "score": 0.0,
        "pass": False,
        "reason": f"Invalid ISO 8601 date: {date_str!r}",
    }
