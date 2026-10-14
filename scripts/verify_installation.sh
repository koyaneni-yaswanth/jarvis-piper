#!/usr/bin/env bash
# JARVIS-PiPER: Installation Verification Script (Phase 2 & Phase 15)
# Non-destructive test script to verify environment and package imports.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

echo "================================================================================"
echo "                   JARVIS-PiPER INSTALLATION VERIFICATION"
echo "================================================================================"

export PYTHONPATH="${REPO_ROOT}:${PYTHONPATH}"

ERRORS=0

echo -n "[1/5] Checking Python interpreter... "
PY_EXE=$(command -v python3 || command -v python)
if [ -z "$PY_EXE" ]; then
    echo "FAIL (python3 not found)"
    ERRORS=$((ERRORS + 1))
else
    PY_VER=$($PY_EXE -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')")
    echo "PASS ($PY_EXE, version $PY_VER)"
fi

echo -n "[2/5] Checking core package imports... "
if $PY_EXE -c "
import numpy
import yaml
import jarvis.safety
import jarvis.hardware
import jarvis.teleop
import jarvis.record
import jarvis.doctor
" 2>/dev/null; then
    echo "PASS"
else
    echo "FAIL (Failed to import jarvis core modules)"
    ERRORS=$((ERRORS + 1))
fi

echo -n "      Checking PyTorch (ML acceleration)... "
if $PY_EXE -c "import torch" 2>/dev/null; then
    echo "PASS (PyTorch installed)"
else
    echo "INFO (PyTorch not installed in this environment; training requires venv)"
fi

echo -n "[3/5] Checking configuration file... "
if [ -f "${REPO_ROOT}/config.yaml" ]; then
    echo "PASS (${REPO_ROOT}/config.yaml exists)"
else
    echo "FAIL (Missing config.yaml)"
    ERRORS=$((ERRORS + 1))
fi

echo -n "[4/5] Checking diagnostic CLI tool... "
if $PY_EXE -m jarvis.cli doctor > /dev/null 2>&1; then
    echo "PASS (jarvis doctor reports clean)"
else
    echo "WARN (jarvis doctor returned non-zero, check hardware warnings)"
fi

echo -n "[5/5] Executing automated test suite... "
if command -v pytest &>/dev/null || $PY_EXE -m pytest --version &>/dev/null; then
    if $PY_EXE -m pytest "${REPO_ROOT}/tests/test_jarvis_release.py" -q > /dev/null 2>&1; then
        echo "PASS (All 14 release acceptance tests passed)"
    else
        echo "FAIL (Release tests failed)"
        ERRORS=$((ERRORS + 1))
    fi
else
    if $PY_EXE -c "
from jarvis.safety import SafetySupervisor
from jarvis.hardware import MockArm, MockTeleop
s = SafetySupervisor()
arm = MockArm()
assert arm.connect()
assert s.is_motion_authorized() is False
" 2>/dev/null; then
        echo "PASS (Core safety smoke test passed; install pytest for full suite)"
    else
        echo "FAIL (Core safety smoke test failed)"
        ERRORS=$((ERRORS + 1))
    fi
fi

echo "================================================================================"
if [ $ERRORS -eq 0 ]; then
    echo " [OK] Installation verified successfully! System is ready for operation."
    exit 0
else
    echo " [ERROR] Installation check failed with $ERRORS errors. Review logs above."
    exit 1
fi
