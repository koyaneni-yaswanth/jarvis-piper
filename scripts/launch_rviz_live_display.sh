#!/usr/bin/env bash
# ==============================================================================
# JARVIS-PiPER: Live RViz2 Visualization Launcher
# Starts passive Robot State Publisher and RViz2 to monitor live PiPER arm & sensors.
# Zero actuation; strictly read-only.
# ==============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Source ROS 2 Humble environment
if [ -f "/opt/ros/humble/setup.bash" ]; then
    source /opt/ros/humble/setup.bash
else
    echo "[ERROR] ROS 2 Humble not found at /opt/ros/humble/setup.bash"
    exit 1
fi

# Source Pika ROS workspace if available
if [ -f "/home/humble/pika_ros/install/setup.bash" ]; then
    source /home/humble/pika_ros/install/setup.bash
fi

echo "================================================================================"
echo "          JARVIS-PiPER :: PASSIVE LIVE RVIZ2 VISUALIZER"
echo "================================================================================"
echo " Kinematic Model: assets/piper/piper.urdf"
echo " RViz Config    : assets/rviz/live_display.rviz"
echo " Feedback Topic : /piper/joint_states"
echo " Mode           : PASSIVE MONITOR (Zero motor commands)"
echo "================================================================================"

cd "${REPO_ROOT}"
ros2 launch launch/rviz_live_display.launch.py "$@"
