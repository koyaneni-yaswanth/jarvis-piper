#!/usr/bin/env bash
# Source this file: source scripts/setup.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export JARVIS_PIPER_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Source genuine ROS 2 Lyrical if available
if [ -f "/opt/ros/lyrical/setup.bash" ]; then
    source "/opt/ros/lyrical/setup.bash"
    echo "[JARVIS-PiPER] Sourced ROS 2 Lyrical (/opt/ros/lyrical/setup.bash)"
elif [ -n "${ROS_DISTRO}" ]; then
    echo "[JARVIS-PiPER] Using existing ROS 2 Distro: ${ROS_DISTRO}"
else
    echo "[JARVIS-PiPER] Note: ROS 2 not installed/sourced. Operating in pure Python / mock mode."
fi

# Source workspace install if built
if [ -f "${JARVIS_PIPER_ROOT}/ros2_ws/install/setup.bash" ]; then
    source "${JARVIS_PIPER_ROOT}/ros2_ws/install/setup.bash"
    echo "[JARVIS-PiPER] Sourced ros2_ws/install/setup.bash"
fi

# Set PYTHONPATH and execution paths
export PYTHONPATH="${JARVIS_PIPER_ROOT}/python:${PYTHONPATH}"
export PATH="${JARVIS_PIPER_ROOT}/scripts:${PATH}"
export ROS_DOMAIN_ID=10
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp

echo "[JARVIS-PiPER] Environment configured. ROS_DOMAIN_ID=${ROS_DOMAIN_ID}"
