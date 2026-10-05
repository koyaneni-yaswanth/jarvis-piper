#!/usr/bin/env bash
set -e

# Source ROS 2 Lyrical if installed
if [ -f "/opt/ros/lyrical/setup.bash" ]; then
    source /opt/ros/lyrical/setup.bash
fi

# Source workspace if built
if [ -f "/workspace/ros2_ws/install/setup.bash" ]; then
    source /workspace/ros2_ws/install/setup.bash
fi

exec "$@"
