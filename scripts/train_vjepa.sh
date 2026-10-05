#!/usr/bin/env bash

EPOCHS="${1:-5}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

export PYTHONPATH="${REPO_ROOT}/python:${PYTHONPATH}"
echo "Training V-JEPA World Model for ${EPOCHS} epochs..."
python3 "${REPO_ROOT}/python/world_model/vjepa/train.py" --config "${REPO_ROOT}/configs/vjepa.yaml" --epochs "${EPOCHS}"
