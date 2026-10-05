#!/usr/bin/env bash
# Trigger episode start or stop recording

CMD="${1:-start}"
TASK="${2:-pick_and_place}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

if command -v ros2 &>/dev/null && [ -n "${ROS_DISTRO}" ]; then
    if [ "$CMD" = "start" ]; then
        echo "Calling ROS 2 StartEpisode service (Task: ${TASK})..."
        ros2 service call /jarvis_piper/recorder/start_episode jarvis_piper_interfaces/srv/StartEpisode "{task_name: '${TASK}', operator: 'operator', notes: 'CLI trigger'}"
    elif [ "$CMD" = "stop" ]; then
        echo "Calling ROS 2 StopEpisode service (Success: true)..."
        ros2 service call /jarvis_piper/recorder/stop_episode jarvis_piper_interfaces/srv/StopEpisode "{success: true, discard: false, notes: 'Completed'}"
    else
        echo "Usage: $0 [start|stop] [task_name]"
    fi
else
    echo "Using JARVIS-PiPER Python CLI..."
    export PYTHONPATH="${REPO_ROOT}/python:${PYTHONPATH}"
    python3 "${REPO_ROOT}/python/jarvis_piper/cli/main.py" "$CMD" --task "${TASK}"
fi
