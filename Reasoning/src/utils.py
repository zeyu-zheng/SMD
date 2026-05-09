import json
import os
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Literal

import yaml

Decision = Literal["PASS", "FIXABLE", "REPLAN", "DISPROVED", "UNKNOWN"]
FinalStatus = Literal["SOLVED", "DISPROVED", "BEST_EFFORT", "NO_RELIABLE_SOLUTION"]


@dataclass
class APIConfig:
    base_url: str | None = None
    base_url_env: str = "GPT_BASE_URL"
    api_key: str | None = None
    api_key_env: str = "GPT_API_KEY"
    api_version: str = "2024-03-01-preview"

    def resolved_base_url(self) -> str:
        return self.base_url or os.environ[self.base_url_env]

    def resolved_key(self) -> str:
        return self.api_key or os.environ[self.api_key_env]


@dataclass
class SearchConfig:
    attempts: int = 8
    verifiers: int = 5
    revisions: int = 3


@dataclass
class Config:
    model: str = "gpt-5.5-2026-04-24"
    reasoning_effort: str = "xhigh"
    web_search: bool = False
    api: APIConfig | None = None
    search: SearchConfig = field(default_factory=SearchConfig)


@dataclass
class VerifierVerdict:
    decision: Decision
    score: float
    confidence: float
    feedback: str
    fatal_gaps: list[str] = field(default_factory=list)
    fix_instructions: str = ""
    replan_reason: str = ""


@dataclass
class AggregateVerdict:
    decision: Decision
    verdicts: list[VerifierVerdict]
    summary: str


@dataclass
class RevisionRecord:
    revision_id: int
    solution: str
    aggregate: AggregateVerdict


@dataclass
class Attempt:
    attempt_id: int
    route: str
    revisions: list[RevisionRecord] = field(default_factory=list)
    status: Decision = "UNKNOWN"


@dataclass
class RunResult:
    status: FinalStatus
    final_answer: str
    attempts: list[Attempt]
    best_solution: str = ""


def load_config(path: str | Path) -> Config:
    data = yaml.safe_load(Path(path).read_text()) or {}
    return Config(
        model=data.get("model", "gpt-5.5-2026-04-24"),
        reasoning_effort=data.get("reasoning_effort", "xhigh"),
        web_search=bool(data.get("web_search", False)),
        api=APIConfig(**data["api"]),
        search=SearchConfig(**(data.get("search") or {})),
    )


def parse_json_object(text: str) -> dict:
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    candidate = match.group(1) if match else text.strip()
    if not candidate.startswith("{"):
        candidate = candidate[candidate.find("{") : candidate.rfind("}") + 1]
    return json.loads(candidate)


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
            (attempt_dir / f"verify_{record.revision_id}.json").write_text(
                json.dumps(asdict(record.aggregate), indent=2, ensure_ascii=False)
            )
    return run_dir
