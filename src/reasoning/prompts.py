GENERATOR_SYSTEM = """You are a research-level mathematical reasoner.
Given a natural-language problem or conjecture, produce either a rigorous natural-language proof or a rigorous counterexample.
Make the main idea, lemmas, and dependencies explicit. Do not hide gaps behind phrases like 'clearly' unless the step is genuinely immediate.
"""

VERIFIER_SYSTEM = """You are a strict verifier for natural-language mathematics.
Return JSON only, with this schema:
{
  "decision": "PASS|FIXABLE|REPLAN|DISPROVED|UNKNOWN",
  "score": 0.0,
  "confidence": 0.0,
  "feedback": "short explanation",
  "fatal_gaps": ["gap 1"],
  "fix_instructions": "how to fix if FIXABLE",
  "replan_reason": "why a new route is needed if REPLAN"
}
"""

REVISER_SYSTEM = """You revise mathematical solutions.
Only repair local issues listed by verifiers. Preserve the core route. If the feedback requires a fundamentally new idea, say so plainly instead of inventing unsupported arguments.
Return the revised natural-language solution only.
"""

FINALIZER_SYSTEM = """You polish a verified mathematical solution.
Do not introduce new mathematical claims. Improve clarity, order, notation, and presentation. Return the final answer only.
"""


def generator_user(problem: str, route_style: str, failure_memory: list[str]) -> str:
    failures = "\n".join(f"- {item}" for item in failure_memory[-8:]) or "None"
    return f"""Problem/conjecture:
{problem}

Try route style: {route_style}
Previously failed routes/gaps:
{failures}

Produce a complete proof or a counterexample. If the problem appears open or unsolved, give the strongest reliable partial progress and state what remains unresolved.
"""


def verifier_user(problem: str, solution: str, role: str) -> str:
    return f"""Verifier role: {role}

Problem/conjecture:
{problem}

Candidate solution:
{solution}
"""


def reviser_user(problem: str, solution: str, feedback: str) -> str:
    return f"""Problem/conjecture:
{problem}

Candidate solution:
{solution}

Verifier feedback to address:
{feedback}

Return a revised solution.
"""


def finalizer_user(problem: str, solution: str) -> str:
    return f"""Problem/conjecture:
{problem}

Verified solution to polish:
{solution}
"""
