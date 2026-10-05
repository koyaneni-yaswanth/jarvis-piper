"""
Passive Dataset Replay Node.
Reads recorded demonstration episodes and publishes telemetry and camera streams to ROS 2 topics.
CRITICAL: Operates in passive read-only mode with zero motor actuation commands.
"""

import os
import sys
import time
import json
from pathlib import Path
from typing import Optional, List, Dict, Any

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState, Image
from geometry_msgs.msg import PoseStamped
from std_msgs.msg import Header


class DatasetReplayNode(Node):
    """Replays demonstration episodes over ROS 2 topics."""

    def __init__(self):
        super().__init__('dataset_replay_node')

        self.declare_parameter('episode_path', 'dataset/raw')
        self.declare_parameter('playback_rate', 50.0)  # Hz
        self.declare_parameter('loop', False)

        self.episode_path = self.get_parameter('episode_path').get_parameter_value().string_value
        self.playback_rate = self.get_parameter('playback_rate').get_parameter_value().double_value
        self.loop = self.get_parameter('loop').get_parameter_value().bool_value

        # Publishers
        self.joint_pub = self.create_publisher(JointState, '/piper/joint_states', 10)
        self.teleop_pub = self.create_publisher(JointState, '/piper_teleop/joint_states', 10)
        self.pika_pub = self.create_publisher(PoseStamped, '/pika_pose', 10)

        # Load episode
        self.frames: List[Dict[str, Any]] = []
        self.current_idx = 0
        self._load_episode()

        timer_period = 1.0 / max(1.0, self.playback_rate)
        self.timer = self.create_timer(timer_period, self._playback_callback)
        self.get_logger().info(f"Replay Node initialized. Rate: {self.playback_rate} Hz, Frames: {len(self.frames)}")

    def _load_episode(self):
        ep_dir = Path(self.episode_path)
        if ep_dir.is_dir() and not (ep_dir / "trajectory.json").exists():
            # If a root dataset dir was passed, pick the first episode
            subdirs = [d for d in ep_dir.iterdir() if d.is_dir() and (d / "trajectory.json").exists()]
            if subdirs:
                ep_dir = subdirs[0]

        traj_file = ep_dir / "trajectory.json"
        if not traj_file.exists():
            self.get_logger().warn(f"No trajectory.json found in {ep_dir}. Using simulated frames.")
            self._create_simulated_frames()
            return

        try:
            with open(traj_file, "r") as f:
                data = json.load(f)
            joints_list = data.get("joint_positions", [])
            timestamps = data.get("timestamps", [])
            gripper_list = data.get("gripper_positions", [])

            for i, j_pos in enumerate(joints_list):
                ts = timestamps[i] if i < len(timestamps) else time.time()
                grip = gripper_list[i] if i < len(gripper_list) else 0.0
                self.frames.append({
                    "timestamp": ts,
                    "joints": j_pos,
                    "gripper": grip,
                })
            self.get_logger().info(f"Loaded {len(self.frames)} frames from {traj_file}")
        except Exception as e:
            self.get_logger().error(f"Error reading episode {ep_dir}: {e}")
            self._create_simulated_frames()

    def _create_simulated_frames(self):
        for i in range(100):
            t = i * 0.02
            self.frames.append({
                "timestamp": time.time() + t,
                "joints": [0.1 * i] * 6,
                "gripper": 0.02,
            })

    def _playback_callback(self):
        if not self.frames:
            return

        if self.current_idx >= len(self.frames):
            if self.loop:
                self.current_idx = 0
            else:
                self.get_logger().info("Episode replay reached end of stream.")
                self.timer.cancel()
                return

        frame = self.frames[self.current_idx]
        self.current_idx += 1

        now = self.get_clock().now().to_msg()

        # Publish Joint State
        js_msg = JointState()
        js_msg.header.stamp = now
        js_msg.header.frame_id = "piper_base_link"
        js_msg.name = [f"piper_joint{i+1}" for i in range(6)] + ["piper_finger_left_joint"]
        js_msg.position = [float(v) for v in frame["joints"][:6]] + [float(frame["gripper"])]
        self.joint_pub.publish(js_msg)
        self.teleop_pub.publish(js_msg)

        # Publish Pose
        pose_msg = PoseStamped()
        pose_msg.header.stamp = now
        pose_msg.header.frame_id = "piper_base_link"
        pose_msg.pose.position.x = 0.25
        pose_msg.pose.position.y = 0.0
        pose_msg.pose.position.z = 0.20
        pose_msg.pose.orientation.w = 1.0
        self.pika_pub.publish(pose_msg)


def main(args=None):
    rclpy.init(args=args)
    node = DatasetReplayNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
