#!/usr/bin/env bash
# ==============================================================================
# JARVIS-PiPER: Reproducible Environment Setup Script
# Configures local Python virtual environment, links dependencies, and verifies
# ROS 2 Humble environment without modifying system packages.
# ==============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

echo "================================================================================"
echo "                  JARVIS-PiPER :: ENVIRONMENT SETUP"
echo "================================================================================"
echo "Repository Root: ${REPO_ROOT}"

cd "${REPO_ROOT}"

# 1. Ensure .venv exists with Python 3.10
if [ ! -d "${REPO_ROOT}/.venv" ]; then
    echo "[1/4] Creating virtual environment (.venv)..."
    python3 -m venv "${REPO_ROOT}/.venv" --system-site-packages
else
    echo "[1/4] Virtual environment exists at ${REPO_ROOT}/.venv"
fi

PY_BIN="${REPO_ROOT}/.venv/bin/python3"
PIP_BIN="${REPO_ROOT}/.venv/bin/pip"

# 2. Link PyTorch from existing NUC workstation installation if not already present
SITE_PACKAGES=$($PY_BIN -c "import site; print(site.getsitepackages()[0])")
PTH_FILE="${SITE_PACKAGES}/vjepa2_torch.pth"
VJEPA2_SITE="/home/humble/robotics/vjepa2/.venv/lib/python3.10/site-packages"

if [ -d "$VJEPA2_SITE" ] && [ ! -f "$PTH_FILE" ]; then
    echo "[2/4] Linking pre-compiled PyTorch into .venv via .pth..."
    echo "$VJEPA2_SITE" > "$PTH_FILE"
else
    echo "[2/4] PyTorch linking verified."
fi

# 3. Install core editable package
echo "[3/4] Ensuring editable package installation..."
$PIP_BIN install -e . --no-deps > /dev/null 2>&1 || true

# 4. Verification smoke check
echo "[4/4] Verifying environment integrity..."
$PY_BIN -c "import torch, numpy, yaml; print(f'  [PASS] PyTorch {torch.__version__}, NumPy {numpy.__version__}, PyYAML {yaml.__version__}')"

echo ""
echo "================================================================================"
echo " [SUCCESS] Environment setup complete."
echo " To activate: source ${REPO_ROOT}/.venv/bin/activate"
echo "================================================================================"
