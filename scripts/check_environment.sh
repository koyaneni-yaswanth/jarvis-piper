#!/usr/bin/env bash
# JARVIS-PiPER: Environment & Dependency Check (Phase 2 & Phase 15)
# Non-destructive inspection of operating system, ROS, Python, and hardware interfaces.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

echo "================================================================================"
echo "                   JARVIS-PiPER :: ENVIRONMENT & RUNTIME CHECK"
echo "================================================================================"

# 1. Operating System
echo -n "Operating System : "
if [ -f /etc/os-release ]; then
    . /etc/os-release
    echo "${PRETTY_NAME} (${ID} ${VERSION_ID}) [Kernel $(uname -r)]"
else
    uname -srm
fi

# 2. Python Interpreter & Conda check
echo -n "Python Path      : "
PY_PATH=$(which python3 2>/dev/null || echo "NOT FOUND")
echo "${PY_PATH} ($(${PY_PATH} --version 2>&1))"

if echo "$PATH" | grep -qiE "conda|miniconda"; then
    echo "  [CAUTION] Conda environment detected in PATH! Conda Python can conflict with ROS 2 binaries."
    echo "            Deactivate Conda ('conda deactivate') when launching ROS 2 Humble nodes."
fi

# 3. ROS 2 Distribution
echo -n "ROS 2 Status     : "
if [ -n "${ROS_DISTRO}" ]; then
    echo "Active distro: ${ROS_DISTRO} (Domain ID: ${ROS_DOMAIN_ID:-0})"
elif [ -f "/opt/ros/humble/setup.bash" ]; then
    echo "Found /opt/ros/humble (ROS 2 Humble ready to source)"
elif [ -f "/opt/ros/lyrical/setup.bash" ]; then
    echo "Found /opt/ros/lyrical (ready to source)"
else
    echo "ROS 2 not active on environment PATH (Mock / Standalone mode active)"
fi

# 4. GPU / Compute Acceleration
echo -n "GPU Acceleration : "
if command -v nvidia-smi &>/dev/null; then
    nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader 2>/dev/null || echo "nvidia-smi error"
else
    echo "No NVIDIA GPU detected (Standard CPU fallback active)"
fi

# 5. SocketCAN Interface
echo -n "CAN Bus (can0)   : "
if command -v ip &>/dev/null && ip link show can0 &>/dev/null; then
    CAN_STATUS=$(ip -br link show can0 | awk '{print $2}')
    echo "Interface can0 is ${CAN_STATUS}"
else
    echo "Not detected / down (Mock mode fallback available)"
fi

# 6. USB Teleop Receiver
echo -n "PIKA USB Dongle  : "
if command -v lsusb &>/dev/null; then
    if lsusb | grep -qiE "28de:|valve|steam"; then
        echo "SteamVR Receiver (0x28de) detected"
    else
        echo "Not detected on USB (Mock teleop fallback available)"
    fi
else
    echo "lsusb not available"
fi

# 7. User Group Permissions
echo -n "User Groups      : "
USER_GROUPS=$(groups 2>/dev/null || true)
if echo "$USER_GROUPS" | grep -q "dialout"; then
    echo "dialout present [PASS]"
else
    echo "dialout MISSING (run: sudo usermod -aG dialout \$USER)"
fi

# 8. Core Python Dependencies
echo "Python Dependencies:"
${PY_PATH:-python3} -c "
import sys
deps = ['numpy', 'yaml', 'PIL', 'cv2', 'torch', 'h5py', 'rclpy']
for d in deps:
    try:
        __import__(d)
        print(f'  - {d:<10}: OK')
    except ImportError:
        print(f'  - {d:<10}: Not installed (fallback / mock available)')
"

echo "================================================================================"
