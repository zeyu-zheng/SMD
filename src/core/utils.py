import argparse
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Callable

from src.core.config import DEFAULT_CONFIG, load_config


def parse_bool(value: str) -> bool:
    text = value.strip().lower()
    if text in {"true", "1", "yes", "y"}:
        return True
    if text in {"false", "0", "no", "n"}:
        return False
    raise argparse.ArgumentTypeError(f"invalid boolean value: {value}")


def extract_first_json(text: str, required_keys: set[str] = set()) -> dict[str, Any] | None:
    decoder = json.JSONDecoder()
    for index, char in enumerate(text):
        if char != "{":
            continue
        try:
            obj, _ = decoder.raw_decode(text[index:])
        except Exception:
            continue
        if isinstance(obj, dict) and required_keys.issubset(obj):
            return obj
    return None


def validate_score(value: Any, name: str) -> float:
    try:
        score = float(value)
    except Exception as exc:
        raise ValueError(f"{name} must be a number in [0, 1]") from exc
    if not 0.0 <= score <= 1.0:
        raise ValueError(f"{name} must be in [0, 1]")
    return score


def paper_text(row: dict[str, Any], max_chars: int) -> str:
    return str(row.get("book_md") or row.get("content") or row.get("text") or "")[:max_chars]


def add_batch_args(parser: argparse.ArgumentParser, output_suffix: str, max_chars: bool = True) -> None:
    parser.add_argument("input", type=Path)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("-o", "--output-suffix", type=str, default=output_suffix, dest="output_suffix")
    parser.add_argument("-j", "--jobs", type=int, default=8)
    parser.add_argument("-n", "--retry-count", type=int, default=3)
    parser.add_argument("--resume", type=parse_bool, default=False)
    if max_chars:
        parser.add_argument("--max-chars", type=int)


def read_rows(path: Path) -> list[dict[str, Any]]:
    if path.suffix == ".jsonl":
        with path.open("r", encoding="utf-8") as file:
            return [json.loads(line) for line in file if line.strip()]
    if path.suffix == ".parquet":
        import pyarrow.parquet as pq

        return pq.read_table(path).to_pylist()
    raise ValueError(f"unsupported input format: {path}")


def append_jsonl(path: Path, item: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(item, ensure_ascii=False) + "\n")


def load_done_ids(path: Path) -> set[int]:
    if not path.exists():
        return set()
    done = set()
    with path.open("r", encoding="utf-8") as file:
        for line in file:
            try:
                row_index = json.loads(line).get("row_index")
            except Exception:
                continue
            if isinstance(row_index, int):
                done.add(row_index)
    return done


def run_rows(args: Any, stage: str, process_row: Callable[[dict[str, Any], Any], dict[str, Any]]) -> None:
    args.config_obj = load_config(args.config)
    input_path = args.input.resolve()
    output_stem = input_path.stem
    for suffix in ("_labeled", "_recalled", "_reranked"):
        if output_stem.endswith(suffix):
            output_stem = output_stem[: -len(suffix)]
            break
    output_path = input_path.with_name(f"{output_stem}{args.output_suffix}.jsonl").resolve()
    rows = read_rows(input_path)
    done_ids = load_done_ids(output_path) if args.resume else set()

    print(f"Input: {input_path}", flush=True)
    print(f"Output: {output_path}", flush=True)
    print(f"Rows: {len(rows)} | Already done: {len(done_ids)} | Jobs: {args.jobs}", flush=True)

    with ThreadPoolExecutor(max_workers=args.jobs) as executor:
        futures = {
            executor.submit(process_with_retries, index, row, args, stage, process_row): index
            for index, row in enumerate(rows)
            if index not in done_ids
        }
        ok_count = 0
        fail_count = 0
        for completed, future in enumerate(as_completed(futures), start=1):
            item = future.result()
            if item.get("status") == "failed":
                fail_count += 1
                print(f"Failed detail: {json.dumps(item, ensure_ascii=False)}", flush=True)
            else:
                ok_count += 1
                append_jsonl(output_path, item)
            print(f"[{completed}/{len(futures)}] row_index={item.get('row_index')} ok={ok_count} failed={fail_count}", flush=True)


def process_with_retries(index: int, row: dict[str, Any], args: Any, stage: str, process_row: Callable[[dict[str, Any], Any], dict[str, Any]]) -> dict[str, Any]:
    last_failure = None
    for attempt in range(1, max(args.retry_count, 1) + 1):
        started_at = time.time()
        try:
            item = process_row(row, args)
            duration = round(time.time() - started_at, 3)
            item.update({"row_index": index, "duration": duration})
            return item
        except Exception as exc:
            last_failure = {
                "row_index": index,
                "attempt": attempt,
                "duration": round(time.time() - started_at, 3),
                "status": "failed",
                "error": f"{stage}_error: {exc}",
            }
    return last_failure
