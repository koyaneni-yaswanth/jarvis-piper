#!/usr/bin/env bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

export PYTHONPATH="${REPO_ROOT}/python:${PYTHONPATH}"
echo "Evaluating V-JEPA World Model..."
python3 "${REPO_ROOT}/python/world_model/vjepa/evaluate.py" --config "${REPO_ROOT}/configs/vjepa.yaml"
