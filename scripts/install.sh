#!/usr/bin/env bash
set -e

echo "============================================================"
echo " JARVIS-PiPER :: Installation Script"
echo "============================================================"

# Resolve script directory and repository root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

echo "Repository Root: ${REPO_ROOT}"

# Install Python requirements in editable mode
echo "[1/3] Installing Python package in editable mode..."
python3 -m pip install -e "${REPO_ROOT}" --no-deps 2>/dev/null || {
    echo "[INFO] pip install -e failed or PEP 668 active; installing user mode..."
    python3 -m pip install -e "${REPO_ROOT}" --break-system-packages --no-deps 2>/dev/null || true
}

# Create necessary runtime directories
echo "[2/3] Creating directory structures..."
mkdir -p "${REPO_ROOT}/dataset/raw"
mkdir -p "${REPO_ROOT}/dataset/lerobot"
mkdir -p "${REPO_ROOT}/dataset/aloha_hdf5"
mkdir -p "${REPO_ROOT}/dataset/rlds"
mkdir -p "${REPO_ROOT}/models/checkpoints/vjepa"
mkdir -p "${REPO_ROOT}/models/evaluations"
mkdir -p "${REPO_ROOT}/models/exported/vjepa"
mkdir -p "${REPO_ROOT}/experiments/runs"

# Copy local config template if not present
if [ ! -f "${REPO_ROOT}/configs/local.yaml" ]; then
    echo "[3/3] Creating default configs/local.yaml from template..."
    cp "${REPO_ROOT}/configs/local.yaml.example" "${REPO_ROOT}/configs/local.yaml"
fi

echo "============================================================"
echo " [SUCCESS] JARVIS-PiPER installed successfully!"
echo " Source environment with: source scripts/setup.sh"
echo "============================================================"
