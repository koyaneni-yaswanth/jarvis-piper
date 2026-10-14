#!/usr/bin/env bash
# ==============================================================================
# JARVIS-PiPER: NUC Preflight Hardware & Environment Inspector
# Non-destructive: Never commands motion, never enables motors, never alters files.
# Validates Gate 1 (Environment) and Gate 2 (Hardware Discovery).
# ==============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

echo "================================================================================"
echo "              JARVIS-PiPER :: PHYSICAL NUC PREFLIGHT INSPECTOR"
echo "================================================================================"

GATE1_PASS=true
GATE2_PASS=true

# ------------------------------------------------------------------------------
# GATE 1: ENVIRONMENT VERIFICATION
# ------------------------------------------------------------------------------
echo ""
echo "--- GATE 1: ENVIRONMENT VERIFICATION ---"

# 1.1 OS Check
if [ -f /etc/os-release ]; then
    . /etc/os-release
    echo "  OS Version      : ${PRETTY_NAME} (${VERSION_ID})"
    if [[ "$VERSION_ID" != "22.04"* ]]; then
        echo "  [WARN] Expected Ubuntu 22.04 LTS; detected ${VERSION_ID}."
    else
        echo "  [PASS] Ubuntu 22.04 LTS confirmed."
    fi
else
    echo "  [WARN] /etc/os-release not found. Non-Linux system detected."
fi

# 1.2 Python Check
PY_EXE=$(command -v python3 || command -v python)
PY_VER=$($PY_EXE -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')")
echo "  Python Version  : $PY_VER ($PY_EXE)"
if echo "$PY_VER" | grep -qE "^3\.(10|11)"; then
    echo "  [PASS] Supported Python version (3.10/3.11)."
else
    echo "  [WARN] Non-standard Python version: $PY_VER (3.10 is recommended for ROS 2 Humble)."
fi

# 1.3 Conda Conflict Check
if echo "$PATH" | grep -qiE "conda|miniconda"; then
    echo "  [FAIL] Active Conda environment detected in PATH!"
    echo "         Action: Run 'conda deactivate' before sourcing ROS 2 Humble."
    GATE1_PASS=false
else
    echo "  [PASS] No active Conda collision detected."
fi

# 1.4 ROS 2 Humble Check
if [ -n "$ROS_DISTRO" ]; then
    echo "  ROS 2 Distro    : $ROS_DISTRO (Active)"
    if [ "$ROS_DISTRO" == "humble" ]; then
        echo "  [PASS] ROS 2 Humble is active."
    else
        echo "  [WARN] ROS_DISTRO is '$ROS_DISTRO' (expected 'humble')."
    fi
elif [ -f "/opt/ros/humble/setup.bash" ]; then
    echo "  [PASS] /opt/ros/humble exists. Source with: source /opt/ros/humble/setup.bash"
else
    echo "  [WARN] /opt/ros/humble not found on this machine."
fi

# 1.5 User Groups
USER_GROUPS=$(groups 2>/dev/null || true)
if echo "$USER_GROUPS" | grep -q "dialout"; then
    echo "  [PASS] User belongs to 'dialout' group."
else
    echo "  [FAIL] User missing from 'dialout' group. Run: sudo usermod -aG dialout \$USER"
    GATE1_PASS=false
fi

# ------------------------------------------------------------------------------
# GATE 2: HARDWARE DEVICE DISCOVERY (NON-DESTRUCTIVE)
# ------------------------------------------------------------------------------
echo ""
echo "--- GATE 2: HARDWARE DEVICE DISCOVERY ---"

# 2.1 SocketCAN Interface
echo -n "  SocketCAN can0  : "
if command -v ip &>/dev/null && ip link show can0 &>/dev/null; then
    STATE=$(ip -br link show can0 | awk '{print $2}')
    echo "Present, State: $STATE"
    if [ "$STATE" == "UP" ]; then
        echo "  [PASS] can0 interface is UP."
    else
        echo "  [FAIL] can0 is $STATE (bring up: sudo ip link set can0 up type can bitrate 1000000)"
        GATE2_PASS=false
    fi
else
    echo "NOT FOUND / DOWN"
    echo "  [FAIL] can0 interface not detected. Check USB-to-CAN adapter connection."
    GATE2_PASS=false
fi

# 2.2 USB-to-CAN Hardware Adapter Enumeration
echo -n "  USB-CAN Adapter : "
if command -v lsusb &>/dev/null; then
    USB_CAN=$(lsusb | grep -iE "can|candle|gs_usb|stm32|0483:5740|1d50:606f" || true)
    if [ -n "$USB_CAN" ]; then
        echo "Detected: $USB_CAN"
        echo "  [PASS] Hardware USB CAN adapter enumerated."
    else
        echo "NOT FOUND"
        echo "  [FAIL] USB-to-CAN adapter not enumerated on USB tree."
        GATE2_PASS=false
    fi
else
    echo "lsusb not available"
fi

# 2.3 SteamVR Wireless Receiver (0x28de)
echo -n "  PIKA SteamVR USB: "
if command -v lsusb &>/dev/null; then
    STEAM_USB=$(lsusb | grep -iE "28de:|valve|steam" || true)
    if [ -n "$STEAM_USB" ]; then
        echo "Detected: $STEAM_USB"
        echo "  [PASS] SteamVR wireless receiver dongle enumerated."
    else
        echo "NOT FOUND"
        echo "  [FAIL] SteamVR dongle (VID 0x28de) not found on USB tree."
        GATE2_PASS=false
    fi
else
    echo "lsusb not available"
fi

# 2.4 libsurvive Optical Calibration Status
echo -n "  libsurvive Calib: "
SURVIVE_CFG="$HOME/.config/libsurvive/config.json"
if [ -f "$SURVIVE_CFG" ]; then
    if grep -q "Lighthouse" "$SURVIVE_CFG" 2>/dev/null; then
        echo "CALIBRATED (Base stations mapped in $SURVIVE_CFG)"
        echo "  [PASS] Optical calibration profile exists."
    else
        echo "NOT_CALIBRATED (config.json exists but lacks base stations)"
        echo "  [WARN] Base stations not calibrated. Run: survive-cli --force-calibrate"
    fi
else
    echo "NOT_CONFIGURED ($SURVIVE_CFG not found)"
    echo "  [INFO] Calibration will be required prior to teleoperation."
fi

# ------------------------------------------------------------------------------
# SUMMARY & VERDICT
# ------------------------------------------------------------------------------
echo ""
echo "================================================================================"
echo "PREFLIGHT VERDICT:"
echo "  Gate 1 (Environment): $( [ "$GATE1_PASS" = true ] && echo 'PASS' || echo 'BLOCKED' )"
echo "  Gate 2 (Hardware)   : $( [ "$GATE2_PASS" = true ] && echo 'PASS' || echo 'BLOCKED' )"
echo "================================================================================"

if [ "$GATE1_PASS" = true ] && [ "$GATE2_PASS" = true ]; then
    echo "[SUCCESS] Host is fully ready for Gate 3 (Feedback Verification)!"
    exit 0
else
    echo "[ACTION REQUIRED] Resolve blocked gates using the remedies above before proceeding."
    exit 1
fi
