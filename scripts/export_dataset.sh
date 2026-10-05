#!/usr/bin/env bash

FORMAT="${1:-all}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

export PYTHONPATH="${REPO_ROOT}/python:${PYTHONPATH}"
echo "Exporting dataset format: ${FORMAT}..."
python3 "${REPO_ROOT}/python/jarvis_piper/cli/main.py" export --format "${FORMAT}"
