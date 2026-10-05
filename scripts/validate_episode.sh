#!/usr/bin/env bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
DATASET_DIR="${1:-${REPO_ROOT}/dataset/raw}"

export PYTHONPATH="${REPO_ROOT}/python:${PYTHONPATH}"
echo "Validating dataset episodes in: ${DATASET_DIR}"
python3 "${REPO_ROOT}/python/jarvis_piper/cli/main.py" validate --dataset "${DATASET_DIR}"
