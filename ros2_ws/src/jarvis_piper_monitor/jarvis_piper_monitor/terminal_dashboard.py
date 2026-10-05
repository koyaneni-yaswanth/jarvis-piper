"""
JARVIS PiPER Live Terminal Dashboard
Renders real-time telemetry, episode status, buffer health, and keyboard shortcuts in CLI.
"""

import os
import sys
import time
from typing import Optional

import rclpy
from rclpy.node import Node
from jarvis_piper_interfaces.msg import RecorderStatus, SynchronizedFrame
from jarvis_piper_interfaces.srv import StartEpisode, StopEpisode, DiscardEpisode


class TerminalDashboardNode(Node):
    """Terminal dashboard monitoring active recording session."""

    def __init__(self):
        super().__init__("jarvis_piper_terminal_dashboard")

        self.sub_status = self.create_subscription(
            RecorderStatus, "/jarvis_piper/recorder_status", self._cb_status, 10
        )
        self.sub_frame = self.create_subscription(
            SynchronizedFrame, "/jarvis_piper/sync_frame", self._cb_frame, 10
        )

        self.last_status: Optional[RecorderStatus] = None
        self.last_frame: Optional[SynchronizedFrame] = None
        self.render_timer = self.create_timer(0.2, self._render)

    def _cb_status(self, msg: RecorderStatus):
        self.last_status = msg

    def _cb_frame(self, msg: SynchronizedFrame):
        self.last_frame = msg

    def _render(self):
        # Clear screen (ANSI escape)
        sys.stdout.write("\033[H\033[J")

        print("=" * 80)
        print("          JARVIS PiPER EMBODIED-AI TELEOPERATION & RECORDER DASHBOARD")
        print("=" * 80)

        # Recording Status
        is_rec = self.last_status.is_recording if self.last_status else False
        state_str = "\033[1;32m[RECORDING]\033[0m" if is_rec else "\033[1;33m[IDLE / STANDBY]\033[0m"
        ep_id = self.last_status.current_episode_id if self.last_status else "None"
        frames = self.last_status.recorded_frames if self.last_status else 0
        elapsed = self.last_status.elapsed_seconds if self.last_status else 0.0
        task_str = self.last_status.active_task_instruction if self.last_status else "No active task"

        print(f" Status:          {state_str}")
        print(f" Active Episode:  {ep_id}")
        print(f" Instruction:     \033[1;36m{task_str}\033[0m")
        print(f" Telemetry:       Frames: {frames:5d} | Elapsed: {elapsed:6.1f}s | FPS: {(frames/elapsed if elapsed>0 else 0.0):4.1f} Hz")
        print("-" * 80)

        # PiPER Arm Joints & Gripper
        if self.last_frame and self.last_frame.joint_state:
            q = list(self.last_frame.joint_state.position)[:6]
            stroke = self.last_frame.gripper_position
            q_str = " | ".join([f"q{i+1}: {val:+.2f}" for i, val in enumerate(q)])
            print(f" Joint Angles:    {q_str}")
            print(f" Gripper Stroke:  {stroke:.4f} m (0.00=closed, 0.035=open)")

            tcp = self.last_frame.tcp_pose.pose
            print(f" End-Effector:    X: {tcp.position.x:+.3f}  Y: {tcp.position.y:+.3f}  Z: {tcp.position.z:+.3f}")
        else:
            print(" Joint Angles:    Waiting for /jarvis_piper/sync_frame...")

        print("=" * 80)
        print(" Service API Endpoints:")
        print("  - Start:   ros2 service call /jarvis_piper/start_episode jarvis_piper_interfaces/srv/StartEpisode '{task_instruction: \"Pick red cube\"}'")
        print("  - Stop:    ros2 service call /jarvis_piper/stop_episode jarvis_piper_interfaces/srv/StopEpisode '{success_label: true}'")
        print("  - Discard: ros2 service call /jarvis_piper/discard_episode jarvis_piper_interfaces/srv/DiscardEpisode '{reason: \"Operator error\"}'")
        print("=" * 80)
        sys.stdout.flush()


def main(args=None):
    rclpy.init(args=args)
    node = TerminalDashboardNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
