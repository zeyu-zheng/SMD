from typing import Any

from src.core.utils import extract_first_json, validate_score

REQUIRED_KEYS = {
    "sources",
    "reason",
    "status",
    "importance",
    "difficulty",
}

STATUSES = {"open", "solved", "invalid"}


def parse_rerank_result(text: str) -> dict[str, Any]:
    obj = extract_first_json(text, REQUIRED_KEYS)
    if obj is None:
        raise ValueError("no rerank JSON object found")

    status = obj.get("status")
    if status not in STATUSES:
        raise ValueError(f"status must be one of {sorted(STATUSES)}")

    return {
        "sources": validate_sources(obj.get("sources")),
        "reason": require_text(obj.get("reason"), "reason"),
        "status": status,
        "importance": validate_score(obj.get("importance"), "importance"),
        "difficulty": validate_score(obj.get("difficulty"), "difficulty"),
    }


def validate_rerank_result(text: str) -> dict[str, Any]:
    try:
        parse_rerank_result(text)
    except Exception as exc:
        return {
            "success": False,
            "message": (
                "Your previous final JSON result was rejected. "
                f"Reason: {exc}. "
                "Reply again with exactly one JSON object. "
                "Ensure status is one of open, solved, or invalid; sources is an array; "
                "reason is a non-empty English string; and importance and difficulty are numbers in [0, 1]."
            ),
        }
    return {"success": True}


def require_text(value: Any, name: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"{name} must be a non-empty string")
    return text


def validate_sources(value: Any) -> list[dict[str, str]]:
    if not isinstance(value, list):
        raise ValueError("sources must be an array")
    sources = []
    for item in value[:8]:
        if not isinstance(item, dict):
            continue
        sources.append({
            "title": str(item.get("title") or "").strip(),
            "url": str(item.get("url") or "").strip(),
            "claim": str(item.get("claim") or "").strip(),
        })
    return sources
