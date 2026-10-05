#!/usr/bin/env bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

echo "============================================================"
echo " JARVIS-PiPER :: Environment and Dependency Check"
echo "============================================================"

# OS
echo -n "Operating System : "
if [ -f /etc/os-release ]; then
    . /etc/os-release
    echo "${PRETTY_NAME} (${ID} ${VERSION_ID})"
else
    uname -srm
fi

# Python
echo -n "Python Version   : "
python3 --version 2>&1 || echo "Python3 NOT found!"

# ROS 2
echo -n "ROS 2 Status     : "
if [ -n "${ROS_DISTRO}" ]; then
    echo "Active distro: ${ROS_DISTRO} (Domain ID: ${ROS_DOMAIN_ID:-default})"
elif [ -f "/opt/ros/lyrical/setup.bash" ]; then
    echo "Found /opt/ros/lyrical (ready to source)"
else
    echo "ROS 2 not active (Mock/Standalone mode available)"
fi

# GPU / CUDA
echo -n "NVIDIA GPU       : "
if command -v nvidia-smi &>/dev/null; then
    nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader 2>/dev/null || echo "nvidia-smi failed"
else
    echo "No nvidia-smi detected (CPU mode active)"
fi

# Disk space
echo -n "Disk Space       : "
df -h "${REPO_ROOT}" | awk 'NR==2 {print "Available: "$4" / Total: "$2}'

# Python modules
echo "Checking Python core dependencies..."
python3 -c "
import sys
deps = ['numpy', 'yaml', 'PIL', 'cv2', 'torch', 'h5py', 'rclpy']
for d in deps:
    try:
        __import__(d)
        print(f'  - {d:<10}: OK')
    except ImportError:
        print(f'  - {d:<10}: Not installed (optional/fallback available)')
"

echo "============================================================"
