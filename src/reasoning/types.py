from dataclasses import dataclass, field
from typing import Literal

Decision = Literal["PASS", "FIXABLE", "REPLAN", "DISPROVED", "UNKNOWN"]
FinalStatus = Literal["SOLVED", "DISPROVED", "BEST_EFFORT", "NO_RELIABLE_SOLUTION"]


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
