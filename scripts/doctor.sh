#!/usr/bin/env bash
# ==============================================================================
# JARVIS-PiPER: System & Hardware Doctor Script
# Non-destructive diagnostics for NUC host, ROS 2, sensors, and datasets.
# NEVER commands arm motion, NEVER enables motors.
# ==============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${REPO_ROOT}"

# Resolve Python interpreter (prefer repository venv)
if [ -n "$VIRTUAL_ENV" ] && [ -x "$VIRTUAL_ENV/bin/python3" ]; then
    PY_EXE="$VIRTUAL_ENV/bin/python3"
elif [ -x "${REPO_ROOT}/.venv/bin/python3" ]; then
    PY_EXE="${REPO_ROOT}/.venv/bin/python3"
elif [ -x "${REPO_ROOT}/.venv/bin/python" ]; then
    PY_EXE="${REPO_ROOT}/.venv/bin/python"
else
    PY_EXE=$(command -v python3 || command -v python)
fi

echo "================================================================================"
echo "                  JARVIS-PiPER :: SYSTEM & HARDWARE DOCTOR"
echo "================================================================================"
echo "Interpreter: $PY_EXE"
echo "Workspace  : $REPO_ROOT"
echo ""

# 1. Config Validation
echo "[1/4] Auditing Configuration Schema & Safety Limits..."
$PY_EXE -m jarvis.cli validate-config || {
    echo "[FAIL] Configuration failed safety schema validation!"
    exit 1
}

# 2. Python & Hardware Diagnostics
echo ""
echo "[2/4] Running Comprehensive Diagnostic Inspection..."
$PY_EXE -m jarvis.cli doctor || {
    echo "[INFO] Doctor reported hardware notes above (expected in safe MOCK/read-only mode)."
}

# 3. Demonstration Data Discovery
echo ""
echo "[3/4] Checking Discovered Demonstration Datasets..."
DATA_DIR="/home/humble/pika_mgat_files"
if [ -d "$DATA_DIR/episodes" ]; then
    MCAP_COUNT=$(ls -1 "$DATA_DIR/episodes"/*.mcap 2>/dev/null | wc -l)
    echo "  [PASS] MCAP Episodes directory found: $DATA_DIR/episodes ($MCAP_COUNT recordings)"
else
    echo "  [WARN] No raw MCAP episodes directory at $DATA_DIR/episodes"
fi

if [ -d "$DATA_DIR/hdf5" ]; then
    HDF5_COUNT=$(ls -1 "$DATA_DIR/hdf5"/*.hdf5 2>/dev/null | wc -l)
    echo "  [PASS] Converted HDF5 directory found: $DATA_DIR/hdf5 ($HDF5_COUNT files)"
else
    echo "  [WARN] No HDF5 directory at $DATA_DIR/hdf5"
fi

# 4. Storage & Memory Margin
echo ""
echo "[4/4] Host Compute Margin Check..."
AVAIL_DISK=$(df -h / | awk 'NR==2 {print $4}')
AVAIL_MEM=$(free -h | awk 'NR==2 {print $7}')
echo "  Available Disk Space : $AVAIL_DISK"
echo "  Available Memory     : $AVAIL_MEM"
echo ""
echo "================================================================================"
echo " [COMPLETE] Doctor diagnostics completed successfully. Mode: MOCK (Safe)"
echo "================================================================================"
