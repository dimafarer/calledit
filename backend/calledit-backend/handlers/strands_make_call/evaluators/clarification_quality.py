"""ClarificationQuality Evaluator — keyword coverage score (0.0-1.0).

Scores the proportion of expected topic keywords that appear in the
ReviewAgent's generated clarification questions. Case-insensitive matching.
All keywords found → 1.0. No keywords found → 0.0. This is Tier 1 (deterministic).
"""


def evaluate_clarification_quality(
    review_output: dict, expected_topics: list, span_id: str = ""
) -> dict:
    """Score keyword coverage in ReviewAgent's clarification questions.

    Args:
        review_output: Parsed review results with "reviewable_sections".
        expected_topics: List of topic keyword strings expected in questions.
        span_id: Trace span ID for traceability.

    Returns:
        {"score": 0.0-1.0, "evaluator": "ClarificationQuality", "span_id": str}
    """
    if not expected_topics:
        return {"score": 1.0, "evaluator": "ClarificationQuality", "span_id": span_id}

    # Collect all questions from reviewable sections
    all_questions = []
    for section in review_output.get("reviewable_sections", []):
        all_questions.extend(section.get("questions", []))

    questions_text = " ".join(all_questions).lower()

    # Count how many expected topics appear in the questions
    found = sum(1 for topic in expected_topics if topic.lower() in questions_text)
    score = found / len(expected_topics)

    return {"score": score, "evaluator": "ClarificationQuality", "span_id": span_id,
            "found_topics": found, "total_topics": len(expected_topics)}
