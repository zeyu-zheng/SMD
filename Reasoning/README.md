# Reasoning

A small standalone reasoning engine for natural-language math problems and conjectures.

It takes one `.md` / `.txt` problem, or a directory of problems, and produces a natural-language solution with a saved verifier trace.

## Setup

Use a Python environment with `openai` and `PyYAML` installed.

```bash
pip install openai PyYAML
```

Set your endpoint and API key. The default `config.yaml` reads them from environment variables:

```bash
export GPT_BASE_URL="your_responses_api_base_url"
export GPT_API_KEY="your_api_key"
```

## Quick start

Run from this repo root:

```bash
./run.sh
```

By default this solves:

```text
examples/imo_1988_p6.md
```

Run a specific file:

```bash
./run.sh path/to/problem.md
```

Run every `.md` / `.txt` file under a directory:

```bash
./run.sh path/to/problems_dir
```

Choose output directory:

```bash
./run.sh path/to/problem.md config.yaml outputs
```

Equivalent environment-variable style:

```bash
INPUT=path/to/problems_dir CONFIG=config.yaml OUT=outputs ./run.sh
```

`run.sh` is intentionally simple:

```bash
python src/main.py "$INPUT" --config "$CONFIG" --out "$OUT"
```

## Config

All user-facing settings are in `config.yaml`:

```yaml
model: gpt-5.5-2026-04-24
reasoning_effort: xhigh
web_search: false

api:
  base_url_env: GPT_BASE_URL
  api_key_env: GPT_API_KEY
  api_version: "2024-03-01-preview"

search:
  attempts: 8
  verifiers: 5
  revisions: 3
```

### Main search knobs

- `attempts`: how many independent solution routes to try.
- `verifiers`: how many verifier checks to run for each candidate. Majority vote decides `PASS`, `FIXABLE`, `REPLAN`, `DISPROVED`, or `UNKNOWN`.
- `revisions`: how many local repair rounds to allow when the verifier says the route is basically correct but fixable.

A good default is:

```yaml
search:
  attempts: 8
  verifiers: 5
  revisions: 3
```

For a quick smoke test:

```yaml
search:
  attempts: 1
  verifiers: 1
  revisions: 0
```

For harder problems, increase `attempts` first, then `verifiers` if false proofs slip through, then `revisions` if solutions are close but incomplete.

### Web search

By default:

```yaml
web_search: false
```

This keeps the engine as pure reasoning. If set to `true`, the API call includes:

```python
tools=[{"type": "web_search_preview"}]
```

Only enable it if the endpoint supports that tool and you want external web search.

## Pipeline

```text
problem
  -> generate candidate solution using a built-in route
  -> verifier ensemble checks the candidate
       PASS      -> polish final answer -> re-verify -> SOLVED
       FIXABLE   -> revise locally -> verify again
       REPLAN    -> remember failure -> try a new route
       DISPROVED -> return counterexample/disproof
       UNKNOWN   -> remember uncertainty -> try a new route
  -> budget exhausted -> BEST_EFFORT / NO_RELIABLE_SOLUTION
```

Attempts share a lightweight `failure_memory`, so later attempts see earlier verifier feedback and are prompted not to repeat failed routes.

## Output

For input:

```text
examples/imo_1988_p6.md
```

with output root `runs`, the engine writes:

```text
runs/imo_1988_p6/
  final.md
  state.json
  attempts/
    attempt_001_direct_proof/
      solution_0.md
      verify_0.json
      solution_1.md
      verify_1.json
```

### `final.md`

The answer to read first:

```md
# Status: SOLVED

...final natural-language proof...
```

Possible statuses:

- `SOLVED`: verifier accepted the final answer.
- `DISPROVED`: a valid disproof/counterexample was found.
- `BEST_EFFORT`: no verified final answer, but the best candidate is saved.
- `NO_RELIABLE_SOLUTION`: no useful candidate was found within budget.

### `state.json`

Full machine-readable trace: status, final answer, all attempts, all verifier verdicts, and best candidate.

### `attempts/`

Human-readable trace files:

- `solution_0.md`: initial candidate for that attempt.
- `verify_0.json`: verifier ensemble result for `solution_0.md`.
- `solution_1.md`, `verify_1.json`, ...: revisions or final polished answer plus verification.

The original problem file is not copied into the output directory.

## Code layout

```text
Reasoning/
  run.sh
  config.yaml
  examples/
    imo_1988_p6.md
  src/
    main.py      # entrypoint: args, input discovery, run loop
    engine.py    # reasoning pipeline and agents
    llm.py       # Azure Responses API client
    prompts.py   # generator / verifier / reviser / finalizer prompts
    utils.py     # config/result dataclasses, JSON parsing, file IO
```

The code is intentionally flat and small: no package install, no test harness, no database, no viewer, no extra orchestration layer.
