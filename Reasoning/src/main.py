import argparse
import asyncio
from pathlib import Path

from engine import ReasoningEngine
from utils import collect_problem_files, load_config, write_result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Reasoning.")
    parser.add_argument("input", help="A .md/.txt problem file or a directory containing them.")
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument("--out", default="runs")
    return parser.parse_args()


async def run() -> None:
    args = parse_args()
    config = load_config(args.config)
    out_root = Path(args.out)
    out_root.mkdir(parents=True, exist_ok=True)

    files = collect_problem_files(Path(args.input))
    if not files:
        raise SystemExit(f"No .md or .txt problem files found: {args.input}")

    for problem_path in files:
        print(f"[Reasoning] solving {problem_path}")
        result = await ReasoningEngine(config).solve(problem_path.read_text())
        run_dir = write_result(problem_path, result, out_root)
        print(f"[Reasoning] {problem_path.name}: {result.status} -> {run_dir}")


if __name__ == "__main__":
    asyncio.run(run())
