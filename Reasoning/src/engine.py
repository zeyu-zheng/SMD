import asyncio

from llm import LLMClient
from prompts import (
    FINALIZER_SYSTEM,
    GENERATOR_SYSTEM,
    REVISER_SYSTEM,
    VERIFIER_SYSTEM,
    finalizer_user,
    generator_user,
    reviser_user,
    verifier_user,
)
from utils import (
    AggregateVerdict,
    Attempt,
    Config,
    Decision,
    RevisionRecord,
    RunResult,
    VerifierVerdict,
    parse_json_object,
)

ROUTES = [
    "direct proof",
    "contradiction or minimal counterexample",
    "construction or counterexample search",
    "invariants, extremal principle, or reduction to known results",
]

VERIFIER_ROLES = [
    "check for fatal proof gaps",
    "look for counterexamples and edge cases",
    "check hidden assumptions and dependency on known theorems",
    "decide whether gaps are locally fixable or need a new route",
    "adversarially verify the final conclusion",
]


class Generator:
    def __init__(self, llm: LLMClient):
        self.llm = llm

    async def run(self, problem: str, route: str, failure_memory: list[str]) -> str:
        return await self.llm.complete([
            {"role": "system", "content": GENERATOR_SYSTEM},
            {"role": "user", "content": generator_user(problem, route, failure_memory)},
        ])


class Verifier:
    def __init__(self, llm: LLMClient, count: int):
        self.llm = llm
        self.count = count

    async def run(self, problem: str, solution: str) -> AggregateVerdict:
        roles = VERIFIER_ROLES[: self.count]
        verdicts = await asyncio.gather(*(self._one(problem, solution, role) for role in roles))
        return self._aggregate(verdicts)

    async def _one(self, problem: str, solution: str, role: str) -> VerifierVerdict:
        raw = await self.llm.complete([
            {"role": "system", "content": VERIFIER_SYSTEM},
            {"role": "user", "content": verifier_user(problem, solution, role)},
        ])
        try:
            data = parse_json_object(raw)
            decision = data.get("decision", "UNKNOWN")
            if decision not in {"PASS", "FIXABLE", "REPLAN", "DISPROVED", "UNKNOWN"}:
                decision = "UNKNOWN"
            return VerifierVerdict(
                decision=decision,
                score=float(data.get("score", 0.0)),
                confidence=float(data.get("confidence", 0.0)),
                feedback=str(data.get("feedback", "")),
                fatal_gaps=list(data.get("fatal_gaps", [])),
                fix_instructions=str(data.get("fix_instructions", "")),
                replan_reason=str(data.get("replan_reason", "")),
            )
        except Exception as exc:
            return VerifierVerdict("UNKNOWN", 0.0, 0.0, f"Unparsable verifier output: {exc}")

    def _aggregate(self, verdicts: list[VerifierVerdict]) -> AggregateVerdict:
        counts = {d: sum(v.decision == d for v in verdicts) for d in ["PASS", "FIXABLE", "REPLAN", "DISPROVED", "UNKNOWN"]}
        majority = max(1, len(verdicts) // 2 + 1)
        if counts["PASS"] >= majority:
            decision: Decision = "PASS"
        elif counts["DISPROVED"] >= majority:
            decision = "DISPROVED"
        elif counts["REPLAN"] >= majority:
            decision = "REPLAN"
        elif counts["FIXABLE"] >= majority:
            decision = "FIXABLE"
        else:
            decision = "UNKNOWN"
        summary = "\n".join(f"[{v.decision}] {v.feedback}" for v in verdicts)
        return AggregateVerdict(decision, verdicts, summary)


class Reviser:
    def __init__(self, llm: LLMClient):
        self.llm = llm

    async def run(self, problem: str, solution: str, verdict: AggregateVerdict) -> str:
        return await self.llm.complete([
            {"role": "system", "content": REVISER_SYSTEM},
            {"role": "user", "content": reviser_user(problem, solution, verdict.summary)},
        ])


class Finalizer:
    def __init__(self, llm: LLMClient):
        self.llm = llm

    async def run(self, problem: str, solution: str) -> str:
        return await self.llm.complete([
            {"role": "system", "content": FINALIZER_SYSTEM},
            {"role": "user", "content": finalizer_user(problem, solution)},
        ])


class ReasoningEngine:
    def __init__(self, config: Config):
        self.config = config
        self.llm = LLMClient(config)
        self.generator = Generator(self.llm)
        self.verifier = Verifier(self.llm, config.search.verifiers)
        self.reviser = Reviser(self.llm)
        self.finalizer = Finalizer(self.llm)

    async def solve(self, problem: str) -> RunResult:
        attempts: list[Attempt] = []
        failure_memory: list[str] = []
        best_solution = ""
        best_score = -1.0
        max_calls = self.config.search.attempts * (self.config.search.verifiers + self.config.search.revisions + 3)

        for attempt_id in range(1, self.config.search.attempts + 1):
            if self.llm.calls >= max_calls:
                break

            route = ROUTES[(attempt_id - 1) % len(ROUTES)]
            solution = await self.generator.run(problem, route, failure_memory)
            attempt = Attempt(attempt_id=attempt_id, route=route)
            attempts.append(attempt)

            for revision_id in range(self.config.search.revisions + 1):
                if self.llm.calls >= max_calls:
                    break

                aggregate = await self.verifier.run(problem, solution)
                attempt.revisions.append(RevisionRecord(revision_id, solution, aggregate))
                attempt.status = aggregate.decision

                avg_score = sum(v.score for v in aggregate.verdicts) / max(len(aggregate.verdicts), 1)
                if avg_score > best_score:
                    best_score = avg_score
                    best_solution = solution

                if aggregate.decision == "PASS":
                    final = await self.finalizer.run(problem, solution)
                    final_check = await self.verifier.run(problem, final)
                    attempt.revisions.append(RevisionRecord(revision_id + 1, final, final_check))
                    if final_check.decision == "PASS":
                        return RunResult("SOLVED", final, attempts, best_solution=final)
                    failure_memory.append("Final polished answer failed re-verification: " + final_check.summary[:800])
                    break

                if aggregate.decision == "FIXABLE":
                    solution = await self.reviser.run(problem, solution, aggregate)
                    continue

                if aggregate.decision == "DISPROVED":
                    return RunResult("DISPROVED", solution, attempts, best_solution=solution)

                failure_memory.append(aggregate.summary[:1000])
                break

        if best_solution:
            return RunResult("BEST_EFFORT", best_solution, attempts, best_solution=best_solution)
        return RunResult("NO_RELIABLE_SOLUTION", "No reliable solution was found within the budget.", attempts)
