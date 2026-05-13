from typing import Any

from src.core.utils import extract_first_json, validate_score

ALLOWED_SUBJECTS = {
    "algebra",
    "number_theory",
    "geometry_topology",
    "analysis",
    "probability_statistics",
    "combinatorics",
    "logic_foundations",
    "applied_mathematics",
    "other_math",
    "non_math_or_mislabeled",
}
SCORE_KEYS = {"importance", "formal_difficulty", "comment", "subject"}


def parse_label_result(text: str) -> dict[str, Any]:
    obj = extract_first_json(text, SCORE_KEYS)
    if obj is None:
        raise ValueError("no scoring JSON object found")
    subject = obj.get("subject")
    comment = obj.get("comment")
    if subject not in ALLOWED_SUBJECTS:
        raise ValueError(f"subject must be one of {sorted(ALLOWED_SUBJECTS)}")
    if not isinstance(comment, str) or not comment.strip():
        raise ValueError("comment is missing or empty")
    return {
        "importance": validate_score(obj.get("importance"), "importance"),
        "formal_difficulty": validate_score(obj.get("formal_difficulty"), "formal_difficulty"),
        "subject": subject,
        "comment": comment.strip(),
    }


def validate_label_result(text: str) -> dict[str, Any]:
    try:
        parse_label_result(text)
    except Exception as exc:
        return {
            "success": False,
            "message": (
                "Your previous final JSON result was rejected. "
                f"Reason: {exc}. "
                "Reply again with exactly one JSON object. "
                "Ensure importance and formal_difficulty are numbers in [0, 1], "
                "subject is one of the allowed enum values, and comment is a non-empty English string."
            ),
        }
    return {"success": True}
