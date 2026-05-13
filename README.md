# SMD

SMD is a staged pipeline for selecting and reasoning about mathematics papers and problems.

## Setup

Use Python 3.11 or newer.

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
```

Set API credentials in your shell. Do not commit secrets to this repository.

```bash
export GPT_BASE_URL='...'
export GPT_API_KEY='...'
export LEANEXPLORE_API_KEY='...'
```

`GPT_BASE_URL` and `GPT_API_KEY` are used by the Azure OpenAI client. `LEANEXPLORE_API_KEY` is used by the label stage for Mathlib evidence through the LeanExplore API.

## Run

The included `dataset/top_2000_combinatorics.jsonl` is already a recalled dataset, so it can be sent directly to rerank:

```bash
bash rerank.sh
```

For raw paper inputs with `book_md`, `content`, or `text`, run the earlier stages first.

Label papers:

```bash
bash label.sh
```

Recall open conjectures or problems from labeled papers:

```bash
bash recall.sh
```

Rerank recalled candidates with stronger current-status verification:

```bash
bash rerank.sh
```

Run natural-language reasoning on problem files:

```bash
bash reasoning.sh
```

The default label concurrency is `MAX_JOBS=15` in `label.sh`, which matches the observed reliable LeanExplore API concurrency. Avoid raising it unless the API limit changes. Rerank defaults to lower concurrency because current-status verification can be slow. The rerank stage currently uses `gpt-5.5-2026-04-24` with `reasoning_effort: high`; `xhigh` can drive the crawl endpoint into very long open-ended status searches and hit the upstream ~1800s cutoff.

## Configuration

Edit `config.yaml` for model and pipeline settings. The current pipeline uses the LeanExplore remote API only; no local LeanExplore index or Hugging Face model cache is required.

`rerank` writes one output line per paper. Each line contains paper metadata once and a `candidates` array with per-conjecture `sources`, `reason`, `status`, `importance`, and `difficulty`.

Each stage can override the global model settings in `config.yaml`: `label`, `recall`, `rerank`, and `reasoning` accept `model` and `reasoning_effort`. Empty values inherit the global defaults. The pipeline does not pass a max-token cap to the LLM API.

Inputs can be `.jsonl` or `.parquet`. Output files are written next to the input with the current stage suffix. The previous stage suffix is replaced, so `papers_labeled.jsonl` becomes `papers_recalled.jsonl` rather than `papers_labeled_recalled.jsonl`.
