#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

export PYTHONPATH="src"
PYTHON_BIN="${PYTHON:-python3}"
if [[ -x ".venv/bin/python" ]]; then
  PYTHON_BIN=".venv/bin/python"
fi

echo "[1/3] Running unit and boundary tests..."
"$PYTHON_BIN" -m pytest

echo "[2/3] Running evals..."
"$PYTHON_BIN" scripts/run_evals.py

echo "[3/3] Running stress tests..."
"$PYTHON_BIN" scripts/run_stress_tests.py
