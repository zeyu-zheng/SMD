from typing import Any

from src.core.utils import extract_first_json, validate_score

TOP_LEVEL_KEYS = {"paper_title", "paper_authors", "decision_basis", "has_open_conjecture", "conjectures"}
CONJECTURE_KEYS = {"conjecture_label", "conjecture_text", "conjecture_section", "difficulty_note", "difficulty"}


def parse_recall_result(text: str) -> dict[str, Any]:
    obj = extract_first_json(text, TOP_LEVEL_KEYS)
    if obj is None:
        raise ValueError("no conjecture JSON object found")
    paper_title = obj.get("paper_title")
    if not isinstance(paper_title, str) or not paper_title.strip():
        raise ValueError("paper_title must be a non-empty string")

    decision_basis = obj.get("decision_basis")
    if not isinstance(decision_basis, str) or not decision_basis.strip():
        raise ValueError("decision_basis must be a non-empty string")

    has_open_conjecture = obj.get("has_open_conjecture")
    if not isinstance(has_open_conjecture, bool):
        raise ValueError("has_open_conjecture must be a boolean")
    return {
        "paper_title": paper_title.strip(),
        "paper_authors": validate_authors(obj.get("paper_authors")),
        "decision_basis": decision_basis.strip(),
        "has_open_conjecture": has_open_conjecture,
        "conjectures": validate_conjectures(obj.get("conjectures"), has_open_conjecture),
    }


def validate_recall_result(text: str) -> dict[str, Any]:
    try:
        parse_recall_result(text)
    except Exception as exc:
        return {
            "success": False,
            "message": (
                "Your previous final JSON result was rejected. "
                f"Reason: {exc}. "
                "Reply again with exactly one JSON object containing "
                "paper_title, paper_authors, decision_basis, has_open_conjecture, and conjectures. "
                "If has_open_conjecture is false, conjectures must be []. "
                "If has_open_conjecture is true, conjectures must list every explicit unresolved statement you found."
            ),
        }
    return {"success": True}


def validate_authors(value: Any) -> list[str]:
    if not isinstance(value, list) or not value:
        raise ValueError("paper_authors must be a non-empty array")
    authors = [author.strip() for author in value if isinstance(author, str) and author.strip()]
    if len(authors) != len(value):
        raise ValueError("paper_authors must contain only non-empty strings")
    return authors


def validate_conjectures(value: Any, has_open_conjecture: bool) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        raise ValueError("conjectures must be an array")
    parsed = []
    for index, item in enumerate(value, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"conjectures[{index}] must be an object")
        if not CONJECTURE_KEYS.issubset(item):
            raise ValueError(f"conjectures[{index}] is missing required keys {sorted(CONJECTURE_KEYS)}")
        label = item.get("conjecture_label")
        text = item.get("conjecture_text")
        section = item.get("conjecture_section")
        difficulty_note = item.get("difficulty_note")
        difficulty = item.get("difficulty")
        if not isinstance(label, str) or not label.strip():
            raise ValueError(f"conjectures[{index}].conjecture_label must be non-empty")
        if not isinstance(text, str) or not text.strip():
            raise ValueError(f"conjectures[{index}].conjecture_text must be non-empty")
        if not isinstance(section, str):
            raise ValueError(f"conjectures[{index}].conjecture_section must be a string")
        if not isinstance(difficulty_note, str) or not difficulty_note.strip():
            raise ValueError(f"conjectures[{index}].difficulty_note must be non-empty")
        parsed.append({
            "conjecture_label": label.strip(),
            "conjecture_text": text.strip(),
            "conjecture_section": section.strip(),
            "difficulty_note": difficulty_note.strip(),
            "difficulty": validate_score(difficulty, "difficulty"),
        })
    if has_open_conjecture and not parsed:
        raise ValueError("has_open_conjecture is true but conjectures is empty")
    if not has_open_conjecture and parsed:
        raise ValueError("has_open_conjecture is false but conjectures is not empty")
    return parsed
