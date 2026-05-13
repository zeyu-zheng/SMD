import argparse
import asyncio
from typing import Any

from src.core.config import stage_config
from src.core.llm import LLMClient
from src.core.utils import add_batch_args, run_rows
from src.rerank.prompts import JSON_ONLY_SYSTEM, RERANK_PROMPT_TEMPLATE
from src.rerank.schema import parse_rerank_result, validate_rerank_result


async def rerank_once(row: dict[str, Any], args: argparse.Namespace) -> dict[str, Any]:
    conjectures = row.get("conjectures") or []
    if not row.get("has_open_conjecture") or not conjectures:
        return {"paper_title": row.get("paper_title", ""), "paper_authors": row.get("paper_authors", []), "has_open_candidate": False, "candidates": []}

    config = stage_config(args.config_obj, "rerank")
    llm = LLMClient(config)
    results = []
    for index, conjecture in enumerate(conjectures, start=1):
        print(f"Reranking candidate {index}/{len(conjectures)} for {row.get('paper_title', '')}", flush=True)
        candidate = {
            "paper_title": row.get("paper_title", ""),
            "paper_authors": row.get("paper_authors", []),
            "conjecture_label": conjecture.get("conjecture_label", ""),
            "conjecture_text": conjecture.get("conjecture_text", ""),
            "conjecture_section": conjecture.get("conjecture_section", ""),
        }
        raw = await llm.complete([
            {"role": "system", "content": JSON_ONLY_SYSTEM},
            {"role": "user", "content": RERANK_PROMPT_TEMPLATE.format(**candidate)},
        ], validate_result=validate_rerank_result, max_no_tool_call=2)
        print(f"Finished candidate {index}/{len(conjectures)} for {row.get('paper_title', '')}", flush=True)
        results.append({
            "candidate_index": index,
            "conjecture_label": candidate["conjecture_label"],
            "conjecture_text": candidate["conjecture_text"],
            "conjecture_section": candidate["conjecture_section"],
            **parse_rerank_result(raw),
        })
    results.sort(key=lambda item: (item["status"] != "open", -item["importance"], item["difficulty"]))
    return {
        "paper_title": row.get("paper_title", ""),
        "paper_authors": row.get("paper_authors", []),
        "has_open_candidate": any(item["status"] == "open" for item in results),
        "candidates": results,
    }


def process_row(row: dict[str, Any], args: argparse.Namespace) -> dict[str, Any]:
    return asyncio.run(rerank_once(row, args))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run SMD rerank pipeline.")
    add_batch_args(parser, "_reranked", max_chars=False)
    return parser.parse_args()


def main() -> None:
    run_rows(parse_args(), "rerank", process_row)


if __name__ == "__main__":
    main()
