#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

export PYTHONPATH="src"

echo "[1/3] Running unit and boundary tests..."
python -m unittest discover -s tests -p 'test_*.py' -v

echo "[2/3] Running evals..."
python scripts/run_evals.py

echo "[3/3] Running stress tests..."
python scripts/run_stress_tests.py
