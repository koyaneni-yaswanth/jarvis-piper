#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

echo "============================================================"
echo "    JARVIS-PiPER :: ZERO-HARDWARE END-TO-END DEMO"
echo "============================================================"

export PYTHONPATH="${REPO_ROOT}/python:${PYTHONPATH}"

echo ""
echo "[Step 1/6] Running System Doctor Diagnostics..."
python3 "${REPO_ROOT}/python/jarvis_piper/cli/main.py" doctor

echo ""
echo "[Step 2/6] Generating Synthetic Demonstration Episodes (Mock Mode)..."
python3 "${REPO_ROOT}/python/jarvis_piper/cli/main.py" demo --episodes 2 --steps 60

echo ""
echo "[Step 3/6] Running Quality Scorer & Validation..."
python3 "${REPO_ROOT}/python/jarvis_piper/cli/main.py" validate --dataset "${REPO_ROOT}/dataset/raw"

echo ""
echo "[Step 4/6] Exporting Universal Datasets (LeRobot, ALOHA HDF5, RLDS)..."
python3 "${REPO_ROOT}/python/jarvis_piper/cli/main.py" export --format all

echo ""
echo "[Step 5/6] Training V-JEPA Visual World Model (Smoke Test)..."
python3 "${REPO_ROOT}/python/jarvis_piper/cli/main.py" train --epochs 2 --batch-size 2

echo ""
echo "[Step 6/6] Evaluating World Model & Generating Visualizations..."
python3 "${REPO_ROOT}/python/jarvis_piper/cli/main.py" evaluate
python3 "${REPO_ROOT}/python/world_model/vjepa/visualize.py" --output "${REPO_ROOT}/experiments/demo_latent_trajectory.png"

echo ""
echo "============================================================"
echo " [SUCCESS] JARVIS-PiPER END-TO-END DEMO COMPLETED!"
echo " All systems verified under zero physical hardware."
echo "============================================================"
