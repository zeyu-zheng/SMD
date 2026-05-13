INPUT_PATH=dataset/top_2000_combinatorics_labeled.jsonl
CONFIG_PATH=config.yaml
MAX_JOBS=15
RETRY_COUNT=5
RESUME=true
OUTPUT_SUFFIX=_recalled

python3 src/recall/recall.py "$INPUT_PATH" --config "$CONFIG_PATH" -j "$MAX_JOBS" -n "$RETRY_COUNT" --resume "$RESUME" -o "$OUTPUT_SUFFIX"
