#!/usr/bin/env bash
# =============================================================================
# JARVIS-PiPER: NUC Recovery Sprint 2 Script
# Automated Safe Git Reconciliation, Python 3.10 venv, and CLI Repair
# =============================================================================
set -e

echo "=== JARVIS-PiPER :: Recovery Sprint 2 Execution ==="
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_DIR}"
echo "[INFO] Working Directory: ${REPO_DIR}"

# -----------------------------------------------------------------------------
# PHASE 1: Establish Current State
# -----------------------------------------------------------------------------
echo ""
echo "--- [PHASE 1] Establishing Current State ---"
echo "Git Top Level: $(git rev-parse --show-toplevel 2>/dev/null || echo 'Not a git repo')"
echo "Current Branch: $(git branch --show-current 2>/dev/null || echo 'Unknown')"
echo "Local HEAD: $(git rev-parse HEAD 2>/dev/null || echo 'None')"
echo "Remote URL: $(git remote get-url origin 2>/dev/null || echo 'No remote')"

# Deactivate Conda if active
if [ -n "${CONDA_DEFAULT_ENV}" ]; then
    echo "[WARN] Active Conda environment detected: ${CONDA_DEFAULT_ENV}"
    echo "[INFO] Deactivating Conda to avoid Python 3.14 collision with ROS 2 Humble..."
    # Attempt conda deactivate if conda is in path
    if command -v conda >/dev/null 2>&1; then
        eval "$(conda shell.bash hook 2>/dev/null)" || true
        conda deactivate || true
    fi
    unset CONDA_DEFAULT_ENV
    unset CONDA_PREFIX
fi

# -----------------------------------------------------------------------------
# PHASE 2: Preserve Local Work Before Git Operations
# -----------------------------------------------------------------------------
echo ""
echo "--- [PHASE 2] Preserving Local Work Before Integration ---"
BACKUP_DIR="${HOME}/jarvis_piper_backup_$(date +%Y%m%d_%H%M%S)"
mkdir -p "${BACKUP_DIR}"
echo "[INFO] Backup target directory: ${BACKUP_DIR}"

# 1. Back up git diff and tracked changes
if git diff --quiet; then
    echo "[INFO] No unstaged changes in working tree."
else
    echo "[INFO] Saving unstaged git diff to backup..."
    git diff > "${BACKUP_DIR}/unstaged_changes.patch"
fi

# 2. Back up specific local modification files
for f in docs/system_inventory.md scripts/install.sh scripts/setup.sh; do
    if [ -f "${f}" ]; then
        mkdir -p "${BACKUP_DIR}/$(dirname "${f}")"
        cp "${f}" "${BACKUP_DIR}/${f}"
        echo "[INFO] Preserved ${f} -> ${BACKUP_DIR}/${f}"
    fi
done

# 3. Check for nested jarvis-piper directory
if [ -d "jarvis-piper" ]; then
    echo "[INFO] Nested clone 'jarvis-piper/' found. Preserving to ${BACKUP_DIR}/nested_jarvis_piper..."
    cp -r jarvis-piper "${BACKUP_DIR}/nested_jarvis_piper"
    mkdir -p tools/diagnostics
    if [ -d "jarvis-piper/scripts" ]; then
        cp -n jarvis-piper/scripts/*.py tools/diagnostics/ 2>/dev/null || true
        echo "[INFO] Extracted unique scripts to tools/diagnostics/:"
        ls -la tools/diagnostics/
    fi
    rm -rf jarvis-piper
    echo "[INFO] Nested 'jarvis-piper/' safely removed after full backup."
fi

# 4. Create rescue branch if there are any uncommitted changes
if ! git diff-index --quiet HEAD -- 2>/dev/null; then
    echo "[INFO] Creating rescue branch 'rescue/nuc-local-state'..."
    git checkout -b "rescue/nuc-local-$(date +%Y%m%d_%H%M%S)"
    git add -A
    git commit -m "chore(backup): preserve local NUC modifications and diagnostic scripts"
    git checkout main
fi

# -----------------------------------------------------------------------------
# PHASE 3: Synchronize Git with Canonical Remote
# -----------------------------------------------------------------------------
echo ""
echo "--- [PHASE 3] Synchronizing with Canonical Remote (origin/main) ---"
git fetch origin main
git checkout main
git pull origin main

# Restore NUC-specific system inventory facts if backed up
if [ -f "${BACKUP_DIR}/docs/system_inventory.md" ]; then
    echo "[INFO] Verifying docs/system_inventory.md against local backup..."
    # If the local backup had valuable NUC hostname or interface notes, preserve them
    cp "${BACKUP_DIR}/docs/system_inventory.md" docs/system_inventory.md
fi

echo "[INFO] Git synchronization complete at commit: $(git rev-parse HEAD)"

# -----------------------------------------------------------------------------
# PHASE 4: Setup Compatible Python 3.10 Virtual Environment
# -----------------------------------------------------------------------------
echo ""
echo "--- [PHASE 4] Setting Up Python 3.10 Virtual Environment ---"
SYSTEM_PYTHON="/usr/bin/python3"

if [ ! -x "${SYSTEM_PYTHON}" ]; then
    echo "[ERROR] ${SYSTEM_PYTHON} not found! Ubuntu 22.04 system Python is required."
    exit 1
fi

PY_VER="$(${SYSTEM_PYTHON} -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
echo "[INFO] Detected system Python: ${SYSTEM_PYTHON} (version ${PY_VER})"

if [ "${PY_VER}" != "3.10" ]; then
    echo "[WARN] Expected Python 3.10 for ROS 2 Humble compatibility, got ${PY_VER}."
fi

# Verify python3.10-venv module is installed
if ! ${SYSTEM_PYTHON} -m venv --help >/dev/null 2>&1; then
    echo "[ERROR] python3-venv is not installed on this system."
    echo "[ACTION REQUIRED] Run: sudo apt-get update && sudo apt-get install -y python3.10-venv python3-pip"
    exit 1
fi

# Create .venv if missing or broken
if [ ! -f ".venv/bin/activate" ]; then
    echo "[INFO] Creating isolated virtual environment '.venv' using ${SYSTEM_PYTHON}..."
    ${SYSTEM_PYTHON} -m venv .venv
fi

# Activate .venv
source .venv/bin/activate
echo "[INFO] Activated virtual environment: $(which python) ($(${SYSTEM_PYTHON} -c 'import sys; print(sys.version)'))"

# -----------------------------------------------------------------------------
# PHASE 5: Install Dependencies & Verify CLI Entry Points
# -----------------------------------------------------------------------------
echo ""
echo "--- [PHASE 5] Installing Dependencies & Repairing CLI ---"
python -m pip install --upgrade pip setuptools wheel
python -m pip install -e ".[dev]"
python -m pip install lark

echo "[INFO] Verifying CLI entry points in .venv:"
which jarvis || echo "[FAIL] jarvis not found"
which jarvis-piper || echo "[FAIL] jarvis-piper not found"

# -----------------------------------------------------------------------------
# PHASE 6: Run Tests & Verification
# -----------------------------------------------------------------------------
echo ""
echo "--- [PHASE 6] Running Automated Test Suite ---"
python -m pytest tests/ -q --tb=short

echo ""
echo "--- Running JARVIS Doctor Diagnostic ---"
jarvis doctor || true

echo ""
echo "============================================================"
echo " [SUCCESS] JARVIS-PiPER Recovery Sprint 2 Complete!"
echo " Backup stored at: ${BACKUP_DIR}"
echo " Active Python: $(which python)"
echo " To use the environment, always run:"
echo "   source ~/robotics/jarvis-piper/.venv/bin/activate"
echo "============================================================"
