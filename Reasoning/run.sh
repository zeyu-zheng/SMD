INPUT=${INPUT:-${1:-examples/imo_1988_p6.md}}
CONFIG=${CONFIG:-${2:-config.yaml}}
OUT=${OUT:-${3:-runs}}

python src/main.py "$INPUT" --config "$CONFIG" --out "$OUT"
