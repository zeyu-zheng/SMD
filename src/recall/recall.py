import argparse
import asyncio
from typing import Any

from src.core.config import stage_config
from src.core.llm import LLMClient
from src.core.utils import add_batch_args, paper_text, run_rows
from src.recall.prompts import JSON_ONLY_SYSTEM, RECALL_PROMPT_TEMPLATE
from src.recall.schema import parse_recall_result, validate_recall_result

DROP_KEYS = {"book_md", "content", "text"}


async def recall_once(row: dict[str, Any], args: argparse.Namespace) -> dict[str, Any]:
    config = args.config_obj
    max_chars = args.max_chars if args.max_chars is not None else config.book_md_max_chars
    book_md = paper_text(row, max_chars)
    raw = await LLMClient(stage_config(config, "recall")).complete([
        {"role": "system", "content": JSON_ONLY_SYSTEM},
        {"role": "user", "content": RECALL_PROMPT_TEMPLATE.format(book_md=book_md)},
    ], validate_result=validate_recall_result, max_no_tool_call=2)
    return parse_recall_result(raw)


def process_row(row: dict[str, Any], args: argparse.Namespace) -> dict[str, Any]:
    merged = dict(row)
    merged.update(asyncio.run(recall_once(row, args)))
    if not args.keep_source:
        for key in DROP_KEYS:
            merged.pop(key, None)
    return merged


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run SMD recall pipeline.")
    add_batch_args(parser, "_recalled")
    parser.add_argument("--keep-source", action="store_true")
    return parser.parse_args()


def main() -> None:
    run_rows(parse_args(), "recall", process_row)


if __name__ == "__main__":
    main()
