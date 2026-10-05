#!/usr/bin/env bash

echo "============================================================"
echo " JARVIS-PiPER :: Physical Hardware Probe"
echo "============================================================"

# CAN interfaces (PiPER arm)
echo "[1/4] Checking CAN interfaces (PiPER Arm)..."
if command -v ip &>/dev/null; then
    can_devs=$(ip link show type can 2>/dev/null || true)
    if [ -n "$can_devs" ]; then
        echo "$can_devs"
    else
        echo "  [INFO] No CAN interface found. Hardware will be connected later."
    fi
else
    echo "  [INFO] 'ip' command not found."
fi

# USB video devices (Sensors / RGBD Cameras)
echo "[2/4] Checking Video Devices (/dev/video*)..."
video_devs=$(ls -la /dev/video* 2>/dev/null || true)
if [ -n "$video_devs" ]; then
    echo "$video_devs"
else
    echo "  [INFO] No /dev/video* devices found. Mock cameras will be used."
fi

# ROS 2 Topics
echo "[3/4] Checking ROS 2 Telemetry Topics..."
if command -v ros2 &>/dev/null && [ -n "${ROS_DISTRO}" ]; then
    topics=$(ros2 topic list 2>/dev/null || true)
    if [ -n "$topics" ]; then
        echo "$topics" | grep -E "pika|piper|camera" || echo "  [INFO] No active PIKA/PiPER topics currently running."
    else
        echo "  [INFO] ROS 2 daemon inactive."
    fi
else
    echo "  [INFO] ROS 2 environment not active."
fi

# Pika startup scripts probe
echo "[4/4] Probing AgileX Pika Startup Scripts in ~/pika_ros..."
if [ -d "$HOME/pika_ros" ]; then
    echo "  [OK] Found $HOME/pika_ros directory:"
    find "$HOME/pika_ros" -maxdepth 2 -name "*.bash" -o -name "*.launch.py" 2>/dev/null || true
else
    echo "  [INFO] ~/pika_ros not present on this machine (will be bridged when connected)."
fi

echo "============================================================"
echo " Probe complete. System is ready for Mock or Real Hardware mode."
echo "============================================================"
