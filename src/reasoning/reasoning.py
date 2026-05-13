import argparse
import asyncio
import json
from dataclasses import asdict
from pathlib import Path

from src.core.config import DEFAULT_CONFIG, load_config, stage_config
from src.reasoning.engine import ReasoningEngine
from src.reasoning.types import RunResult


def collect_problem_files(path: Path) -> list[Path]:
    if path.is_file():
        return [path]
    return sorted(p for p in path.rglob("*") if p.suffix.lower() in {".md", ".txt"})


def write_result(problem_path: Path, result: RunResult, out_root: Path) -> Path:
    run_dir = out_root / problem_path.stem
    attempts_dir = run_dir / "attempts"
    attempts_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "final.md").write_text(f"# Status: {result.status}\n\n{result.final_answer}\n")
    (run_dir / "state.json").write_text(json.dumps(asdict(result), indent=2, ensure_ascii=False))
    for attempt in result.attempts:
        route = attempt.route.replace(" ", "_").replace("/", "_")
        attempt_dir = attempts_dir / f"attempt_{attempt.attempt_id:03d}_{route}"
        attempt_dir.mkdir(parents=True, exist_ok=True)
        for record in attempt.revisions:
            (attempt_dir / f"solution_{record.revision_id}.md").write_text(record.solution)
            (attempt_dir / f"verify_{record.revision_id}.json").write_text(json.dumps(asdict(record.aggregate), indent=2, ensure_ascii=False))
    return run_dir


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run SMD reasoning.")
    parser.add_argument("input")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--out", type=Path, default=Path("runs"))
    return parser.parse_args()


async def run() -> None:
    args = parse_args()
    config = stage_config(load_config(args.config), "reasoning")
    args.out.mkdir(parents=True, exist_ok=True)
    files = collect_problem_files(Path(args.input))
    if not files:
        raise SystemExit(f"No .md or .txt problem files found: {args.input}")
    for problem_path in files:
        print(f"[Reasoning] solving {problem_path}")
        result = await ReasoningEngine(config).solve(problem_path.read_text())
        print(f"[Reasoning] {problem_path.name}: {result.status} -> {write_result(problem_path, result, args.out)}")


if __name__ == "__main__":
    asyncio.run(run())
