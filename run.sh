#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
INPUT_DIR="${1:-$SCRIPT_DIR/images}"
OUTPUT_PATH="${2:-$SCRIPT_DIR/output.csv}"
python3 "$SCRIPT_DIR/extractor.py" --input "$INPUT_DIR" --output "$OUTPUT_PATH"
echo "CSV generato: $OUTPUT_PATH"
