#!/usr/bin/env bash
set -euo pipefail
if ! command -v brew >/dev/null 2>&1; then
  echo "Homebrew non trovato. Installa Homebrew da https://brew.sh/"
  exit 1
fi
brew list --versions tesseract >/dev/null 2>&1 || brew install tesseract
brew list --versions tesseract-lang >/dev/null 2>&1 || brew install tesseract-lang
echo "Dipendenze installate"
