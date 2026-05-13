INPUT_PATH=dataset/top_2000_combinatorics.jsonl
CONFIG_PATH=config.yaml
MAX_JOBS=4
RETRY_COUNT=3
RESUME=true
OUTPUT_SUFFIX=_reranked

python3 src/rerank/rerank.py "$INPUT_PATH" --config "$CONFIG_PATH" -j "$MAX_JOBS" -n "$RETRY_COUNT" --resume "$RESUME" -o "$OUTPUT_SUFFIX"
