import argparse
import asyncio
from functools import lru_cache
from typing import Any

from lean_explore.api import ApiClient

from src.core.config import stage_config
from src.core.llm import LLMClient
from src.core.utils import add_batch_args, paper_text, run_rows
from src.label.prompts import JSON_ONLY_SYSTEM, LABEL_PROMPT_TEMPLATE
from src.label.schema import parse_label_result, validate_label_result

MATHLIB_SEARCH_TOOL = {
    "type": "function",
    "name": "mathlib_search",
    "description": "Search Mathlib using semantic retrieval. Use complete natural language statements that express mathematical claims, conditions, or definitions; more precise descriptions usually yield better matches.",
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The search query string, such as a natural language description or a piece of Lean code. Examples: 'If m divides n and n divides p, then m divides p', 'The floor of x plus the floor of y is less than or equal to the floor of x + y', 'Every injective function from a finite set to itself is also surjective'.",
            },
            "limit": {
                "type": "integer",
                "default": 5,
                "description": "Maximum number of matched Lean items to return (1-20).",
            },
        },
        "required": ["query"],
    },
}


@lru_cache(maxsize=1)
def lean_explore_client() -> ApiClient:
    return ApiClient(timeout=30.0)


async def mathlib_search(arguments: dict[str, Any]) -> dict[str, Any]:
    return await lean_explore_search(arguments.get("query", ""), arguments.get("limit", 5))


async def lean_explore_search(query: str, limit: int) -> dict[str, Any]:
    text = str(query or "").strip()
    if not text:
        return {"success": False, "error": "query is required"}

    try:
        n = max(1, min(int(limit), 20))
    except Exception:
        n = 5

    try:
        response = await lean_explore_client().search(
            query=text,
            limit=n,
            packages=["Mathlib"],
        )
        payload = response.model_dump() if hasattr(response, "model_dump") else dict(response)
        return {"success": True, "backend": "LeanExplore:api", **payload}
    except Exception as exc:
        return {"success": False, "error": f"LeanExplore search failed: {exc}", "backend": "LeanExplore:api"}


async def label_once(row: dict[str, Any], args: argparse.Namespace) -> dict[str, Any]:
    config = args.config_obj
    max_chars = args.max_chars if args.max_chars is not None else config.book_md_max_chars
    book_md = paper_text(row, max_chars)
    llm = LLMClient(stage_config(config, "label"))

    raw = await llm.complete([
        {"role": "system", "content": JSON_ONLY_SYSTEM},
        {"role": "user", "content": "You must call the mathlib_search tool before answering. Do not answer from memory.\n\n" + LABEL_PROMPT_TEMPLATE.format(book_md=book_md)},
    ], tools=[MATHLIB_SEARCH_TOOL], tool_handlers={"mathlib_search": mathlib_search}, validate_result=validate_label_result, validate_no_tool_call=validate_label_tool_usage, max_no_tool_call=1)
    return parse_label_result(raw)


def validate_label_tool_usage(called_tools: set[str]) -> dict[str, Any]:
    if "mathlib_search" in called_tools:
        return {"success": True}
    return {
        "success": False,
        "message": (
            "You must call mathlib_search for the main concepts of the paper before giving any final JSON result. "
            "Do not answer from memory. After searching, reply again with exactly one JSON object."
        ),
    }


def process_row(row: dict[str, Any], args: argparse.Namespace) -> dict[str, Any]:
    result = asyncio.run(label_once(row, args))
    merged = dict(row)
    merged.update({
        "paper_title": row.get("paper_title", ""),
        "paper_authors": row.get("paper_authors", []),
        **result,
    })
    return merged


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run SMD label pipeline.")
    add_batch_args(parser, "_labeled")
    return parser.parse_args()


def main() -> None:
    run_rows(parse_args(), "label", process_row)


if __name__ == "__main__":
    main()
