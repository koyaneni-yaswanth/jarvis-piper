#!/usr/bin/env bash
# ==============================================================================
# JARVIS-PiPER: Idempotent Single-Command Installation Script
# Usage:
#   ./install.sh           # Local environment setup and verification
#   ./install.sh --system  # Interactive system configuration (udev, CAN, groups)
# ==============================================================================

set -e

echo "================================================================================"
echo "                       JARVIS-PiPER INSTALLER"
echo "================================================================================"

# 1. Environment and Architecture Inspection
ARCH=$(uname -m)
OS=$(uname -s)

echo "Detected OS: $OS ($ARCH)"
if [ "$OS" != "Linux" ]; then
    echo "Warning: Target hardware execution is supported on Linux (Ubuntu 22.04 LTS)."
fi

# 2. Virtual Environment / Dependency Setup
if command -v python3 &>/dev/null; then
    PY_VER=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    echo "Using Python: $PY_VER"
else
    echo "Error: python3 is not installed!"
    exit 1
fi

echo "Installing package in editable development mode..."
python3 -m pip install --upgrade pip
python3 -m pip install -e .

# 3. Optional System-Level Configuration
if [ "$1" == "--system" ]; then
    echo ""
    echo "--------------------------------------------------------------------------------"
    echo " SYSTEM HARDWARE CONFIGURATION STEP (UDEV, CAN, GROUPS)"
    echo "--------------------------------------------------------------------------------"
    
    echo "1. Adding user $USER to dialout group (for USB/CAN permissions)..."
    echo "   Command: sudo usermod -aG dialout $USER"
    read -p "Apply this change? [y/N]: " CONFIRM_GROUP
    if [[ "$CONFIRM_GROUP" =~ ^[Yy]$ ]]; then
        sudo usermod -aG dialout $USER
        echo "   [APPLIED] User added to dialout group."
    fi

    echo "2. Installing SteamVR udev rule for PIKA Sense..."
    echo "   File: /etc/udev/rules.d/81-vive.rules"
    echo "   Command: sudo cp ros2_ws/src/jarvis_piper_teleop/udev/81-vive.rules /etc/udev/rules.d/ && sudo udevadm control --reload-rules"
    read -p "Apply this change? [y/N]: " CONFIRM_UDEV
    if [[ "$CONFIRM_UDEV" =~ ^[Yy]$ ]]; then
        if [ -f "ros2_ws/src/jarvis_piper_teleop/udev/81-vive.rules" ]; then
            sudo cp ros2_ws/src/jarvis_piper_teleop/udev/81-vive.rules /etc/udev/rules.d/
            sudo udevadm control --reload-rules && sudo udevadm trigger
            echo "   [APPLIED] SteamVR udev rules active."
        fi
    fi

    echo "3. SocketCAN can0 Bringup Helper..."
    echo "   Command: sudo ip link set can0 up type can bitrate 1000000"
    echo "   (Undo: sudo ip link set can0 down)"
    read -p "Attempt bringup of can0 now? [y/N]: " CONFIRM_CAN
    if [[ "$CONFIRM_CAN" =~ ^[Yy]$ ]]; then
        sudo ip link set can0 up type can bitrate 1000000 || echo "   [NOTE] can0 device not detected on bus."
    fi
fi

# 4. Verification Check
echo ""
echo "Running 'python3 -m jarvis.cli doctor' verification..."
python3 -m jarvis.cli doctor

echo ""
echo "================================================================================"
echo " [SUCCESS] JARVIS-PiPER installation and verification complete!"
echo " Consult USER_MANUAL.md to proceed with calibration and demonstration collection."
echo "================================================================================"
