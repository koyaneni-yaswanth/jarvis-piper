#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

echo "============================================================"
echo " JARVIS-PiPER :: Building ROS 2 Workspace"
echo "============================================================"

if [ -f "/opt/ros/lyrical/setup.bash" ]; then
    source "/opt/ros/lyrical/setup.bash"
elif [ -n "${ROS_DISTRO}" ]; then
    echo "Using active ROS 2: ${ROS_DISTRO}"
else
    echo "[ERROR] ROS 2 is not sourced. Please install or source ROS 2 before building ros2_ws."
    exit 1
fi

cd "${REPO_ROOT}/ros2_ws"

echo "Building packages with colcon..."
colcon build --symlink-install --cmake-args -DCMAKE_BUILD_TYPE=Release

echo "============================================================"
echo " [SUCCESS] ROS 2 workspace built successfully!"
echo " Run: source ${REPO_ROOT}/ros2_ws/install/setup.bash"
echo "============================================================"
