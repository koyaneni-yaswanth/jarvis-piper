#!/usr/bin/env bash
# ==============================================================================
# JARVIS-PiPER: NUC Test Runner
# Executes automated test suite on Ubuntu 22.04 / ROS 2 Humble environment.
# STRICTLY ISOLATED: Tests use Mock / Simulation interfaces only; zero hardware motion.
# ==============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

echo "================================================================================"
echo "                   JARVIS-PiPER :: NUC TEST RUNNER"
echo "================================================================================"

cd "${REPO_ROOT}"

# 1. Check Python Interpreter
PY_EXE=$(command -v python3 || command -v python)
if [ -z "$PY_EXE" ]; then
    echo "[ERROR] python3 not found on PATH."
    exit 1
fi

PY_VER=$($PY_EXE -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')")
echo "Python Interpreter: $PY_EXE (v$PY_VER)"

# 2. Check for Conda collision
if echo "$PATH" | grep -qiE "conda|miniconda"; then
    echo "[WARNING] Conda environment detected in PATH. If ROS 2 symbols fail, run 'conda deactivate'."
fi

# 3. Check for Pytest
if ! $PY_EXE -m pytest --version &>/dev/null; then
    echo "[ERROR] pytest is not installed in this Python environment."
    echo "        Run: pip install -e .[dev]   (or: pip install pytest)"
    exit 1
fi

# 4. Configuration Validation Smoke
echo ""
echo "[Step 1/3] Validating configuration schema and safety boundaries..."
$PY_EXE -m jarvis.cli validate-config || {
    echo "[FAIL] Configuration validation failed!"
    exit 1
}

# 5. Doctor Diagnostics Smoke
echo ""
echo "[Step 2/3] Running doctor diagnostic check..."
$PY_EXE -m jarvis.cli doctor || {
    echo "[WARN] Doctor reported warnings (review non-destructive hints above)."
}

# 6. Full Automated Test Suite Execution
echo ""
echo "[Step 3/3] Running full automated test suite (Mock / Safety / Unit)..."
$PY_EXE -m pytest tests/ -v --tb=short

TEST_EXIT=$?
echo ""
echo "================================================================================"
if [ $TEST_EXIT -eq 0 ]; then
    echo " [PASS] All NUC software tests passed cleanly!"
    exit 0
else
    echo " [FAIL] Test suite failed with exit code $TEST_EXIT."
    exit $TEST_EXIT
fi
