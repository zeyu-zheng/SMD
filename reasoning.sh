INPUT_PATH=examples/imo_1988_p6.md
CONFIG_PATH=config.yaml
OUTPUT_DIR=runs

python3 src/reasoning/reasoning.py "$INPUT_PATH" --config "$CONFIG_PATH" --out "$OUTPUT_DIR"
