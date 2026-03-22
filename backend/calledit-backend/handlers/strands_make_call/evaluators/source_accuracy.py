"""SourceAccuracy Evaluator — deterministic planned-source coverage score.

Measures whether evidence sources in the Verification_Outcome correspond to
the sources suggested in the Verification_Plan's `source` field.

Score = proportion of planned sources that fuzzy-match (domain-level) at least
one evidence source. When planned sources is empty, score = 1.0 (nothing to miss).
When score < 1.0, a lightweight LLM call classifies the delta root cause.

This is a deterministic evaluator following the tool_alignment.py pattern.
"""

import logging
from typing import Optional
from urllib.parse import urlparse

try:
    from evaluators.delta_classifier import classify_delta
except ImportError:
    from .delta_classifier import classify_delta

logger = logging.getLogger(__name__)


def _extract_domain(source: str) -> str:
    """Extract domain from a URL, or return lowered source for non-URLs.

    For URLs like "https://www.weather.gov/forecast" → "weather.gov"
    For non-URLs like "weather.gov" → "weather.gov"
    """
    source = source.strip()
    try:
        parsed = urlparse(source)
        if parsed.scheme and parsed.netloc:
            # It's a URL — extract the domain
            domain = parsed.netloc.lower()
            # Strip www. prefix
            if domain.startswith("www."):
                domain = domain[4:]
            return domain
    except Exception:
        pass
    # Non-URL: return lowered string
    return source.lower()


def _fuzzy_domain_match(planned: str, evidence: str) -> bool:
    """Check if a planned source fuzzy-matches an evidence source.

    For URL sources: compare extracted domains.
    For non-URL sources: case-insensitive substring matching.
    """
    planned_domain = _extract_domain(planned)
    evidence_domain = _extract_domain(evidence)

    # Direct domain match
    if planned_domain == evidence_domain:
        return True

    # Substring match (handles cases like "weather.gov" matching
    # "api.weather.gov" or partial domain references)
    if planned_domain in evidence_domain or evidence_domain in planned_domain:
        return True

    return False


def _normalize_sources(source_field) -> list:
    """Normalize the plan's source field to a list of strings.

    The source field can be a string or a list of strings.
    """
    if source_field is None:
        return []
    if isinstance(source_field, str):
        return [source_field] if source_field.strip() else []
    if isinstance(source_field, list):
        return [s for s in source_field if isinstance(s, str) and s.strip()]
    return []


def evaluate_source_accuracy(
    verification_plan: dict,
    verification_outcome: dict,
) -> dict:
    """Score source overlap between plan and execution evidence.

    Args:
        verification_plan: Dict with at least a 'source' field (str or list).
        verification_outcome: Dict with at least an 'evidence' field (list of
            dicts each containing a 'source' key).

    Returns:
        {"score": float, "evaluator": "SourceAccuracy",
         "planned_sources": list, "evidence_sources": list,
         "matched": list, "unmatched_plan": list, "unmatched_evidence": list,
         "delta_classification": str|None}
    """
    planned_sources = _normalize_sources(verification_plan.get("source"))

    evidence_list = verification_outcome.get("evidence", [])
    evidence_sources = []
    for item in evidence_list:
        if isinstance(item, dict):
            src = item.get("source", "")
            if isinstance(src, str) and src.strip():
                evidence_sources.append(src)

    # Match each planned source against evidence sources
    matched = []
    unmatched_plan = []
    for ps in planned_sources:
        found = any(_fuzzy_domain_match(ps, es) for es in evidence_sources)
        if found:
            matched.append(ps)
        else:
            unmatched_plan.append(ps)

    # Find evidence sources not matched by any planned source
    unmatched_evidence = []
    for es in evidence_sources:
        found = any(_fuzzy_domain_match(ps, es) for ps in planned_sources)
        if not found:
            unmatched_evidence.append(es)

    # Score = proportion of planned sources matched
    if len(planned_sources) == 0:
        score = 1.0
    else:
        score = len(matched) / len(planned_sources)

    delta_classification: Optional[str] = None
    if score < 1.0:
        reasoning = verification_outcome.get("reasoning", "")
        delta_classification = classify_delta(
            plan_field="sources",
            planned_items=planned_sources,
            actual_items=evidence_sources,
            reasoning=reasoning,
        )

    return {
        "score": score,
        "evaluator": "SourceAccuracy",
        "planned_sources": planned_sources,
        "evidence_sources": evidence_sources,
        "matched": matched,
        "unmatched_plan": unmatched_plan,
        "unmatched_evidence": unmatched_evidence,
        "delta_classification": delta_classification,
    }
