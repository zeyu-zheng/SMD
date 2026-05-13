import os
from dataclasses import dataclass, field, replace
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = ROOT / "config.yaml"


@dataclass
class APIConfig:
    base_url: str | None = None
    base_url_env: str = "GPT_BASE_URL"
    api_key: str | None = None
    api_key_env: str = "GPT_API_KEY"
    api_version: str = "2024-03-01-preview"
    timeout: float = 1800.0

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
class StageConfig:
    model: str | None = None
    reasoning_effort: str | None = None


@dataclass
class Config:
    model: str = "gpt-5.5-2026-04-24"
    reasoning_effort: str | None = None
    book_md_max_chars: int = 64000
    api: APIConfig = field(default_factory=APIConfig)
    search: SearchConfig = field(default_factory=SearchConfig)
    label: StageConfig = field(default_factory=StageConfig)
    recall: StageConfig = field(default_factory=StageConfig)
    rerank: StageConfig = field(default_factory=StageConfig)
    reasoning: StageConfig = field(default_factory=StageConfig)


def load_config(path: str | Path = DEFAULT_CONFIG) -> Config:
    data = yaml.safe_load(Path(path).read_text()) or {}
    return Config(
        model=data.get("model", Config.model),
        reasoning_effort=data.get("reasoning_effort"),
        book_md_max_chars=int(data.get("book_md_max_chars", Config.book_md_max_chars)),
        api=APIConfig(**(data.get("api") or {})),
        search=SearchConfig(**(data.get("search") or {})),
        label=StageConfig(**(data.get("label") or {})),
        recall=StageConfig(**(data.get("recall") or {})),
        rerank=StageConfig(**(data.get("rerank") or {})),
        reasoning=StageConfig(**(data.get("reasoning") or {})),
    )


def stage_config(config: Config, stage: str) -> Config:
    override = getattr(config, stage)
    return replace(
        config,
        model=override.model or config.model,
        reasoning_effort=override.reasoning_effort if override.reasoning_effort is not None else config.reasoning_effort,
    )
