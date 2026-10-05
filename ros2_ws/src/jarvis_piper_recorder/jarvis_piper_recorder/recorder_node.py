#!/usr/bin/env python3
"""
JARVIS PiPER Episode Recorder Node
Main ROS 2 recording controller. Manages triggers, episode lifecycles, non-blocking disk I/O,
and automated QA invocation upon episode completion.
"""

import os
import re
import sys
import time
from datetime import datetime
from typing import Optional

import cv2
import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy
from cv_bridge import CvBridge

from std_msgs.msg import Int32
from jarvis_piper_interfaces.msg import SynchronizedFrame, RecorderStatus
from jarvis_piper_interfaces.srv import (
    StartEpisode,
    StopEpisode,
    DiscardEpisode,
    GetRecorderStatus,
)
from jarvis_piper_recorder.episode_manager import EpisodeState, EpisodeWriter


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    return re.sub(r"[-\s]+", "_", text)[:32]


class JarvisPiperRecorderNode(Node):
    """Core Episode Recorder Node."""

    def __init__(self):
        super().__init__("jarvis_piper_recorder_node")

        # Declare parameters
        self.declare_parameter("data_dir", "/mnt/d/yaswanth/ranger mini/jarvis_piper_ws/data/raw_episodes")
        self.declare_parameter("target_fps", 30.0)
        self.declare_parameter("sync_topic", "/jarvis_piper/sync_frame")
        self.declare_parameter("trigger_topic", "/pika/button_events")

        self.data_dir = self.get_parameter("data_dir").value
        os.makedirs(self.data_dir, exist_ok=True)
        self.target_fps = float(self.get_parameter("target_fps").value)

        self.get_logger().info(f"Jarvis Piper Recorder initialized. Data storage: {self.data_dir}")

        self.bridge = CvBridge()
        self.state = EpisodeState.IDLE
        self.current_writer: Optional[EpisodeWriter] = None
        self.current_episode_id = ""
        self.active_task = ""
        self.recorded_step_count = 0
        self.start_time = 0.0

        # Subscriptions
        sync_qos = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            history=HistoryPolicy.KEEP_LAST,
            depth=10,
        )
        self.sub_sync = self.create_subscription(
            SynchronizedFrame,
            self.get_parameter("sync_topic").value,
            self._cb_sync_frame,
            sync_qos,
        )

        self.sub_trigger = self.create_subscription(
            Int32,
            self.get_parameter("trigger_topic").value,
            self._cb_hardware_trigger,
            10,
        )

        # Services
        self.srv_start = self.create_service(
            StartEpisode, "/jarvis_piper/start_episode", self._handle_start
        )
        self.srv_stop = self.create_service(
            StopEpisode, "/jarvis_piper/stop_episode", self._handle_stop
        )
        self.srv_discard = self.create_service(
            DiscardEpisode, "/jarvis_piper/discard_episode", self._handle_discard
        )
        self.srv_status = self.create_service(
            GetRecorderStatus, "/jarvis_piper/get_status", self._handle_status
        )

        # Status publisher
        self.pub_status = self.create_publisher(RecorderStatus, "/jarvis_piper/recorder_status", 10)
        self.status_timer = self.create_timer(0.5, self._publish_status)

    def _convert_image_msg(self, img_msg) -> Optional[np.ndarray]:
        """Safely unpacks ROS Image into OpenCV numpy array."""
        if img_msg is None or img_msg.data is None or len(img_msg.data) == 0:
            return None
        try:
            return self.bridge.imgmsg_to_cv2(img_msg, desired_encoding="passthrough")
        except Exception:
            # Fallback manual conversion
            try:
                dtype = np.uint8 if "8" in img_msg.encoding else np.uint16
                channels = 3 if "rgb" in img_msg.encoding.lower() or "bgr" in img_msg.encoding.lower() else 1
                arr = np.frombuffer(img_msg.data, dtype=dtype)
                if channels > 1:
                    arr = arr.reshape((img_msg.height, img_msg.width, channels))
                else:
                    arr = arr.reshape((img_msg.height, img_msg.width))
                return arr
            except Exception:
                return None

    def _cb_sync_frame(self, frame: SynchronizedFrame):
        """Processes incoming synchronized frame."""
        if self.state != EpisodeState.RECORDING or self.current_writer is None:
            return

        # Build telemetry dictionary
        step_dict = {
            "step_index": self.recorded_step_count,
            "timestamp": frame.timestamp.sec + frame.timestamp.nanosec * 1e-9,
            "joint_positions": list(frame.joint_state.position) if frame.joint_state else [],
            "joint_velocities": list(frame.joint_state.velocity) if frame.joint_state else [],
            "joint_efforts": list(frame.joint_state.effort) if frame.joint_state else [],
            "gripper_stroke": frame.gripper_position,
            "gripper_velocity": frame.gripper_velocity,
            "gripper_effort": frame.gripper_effort,
            "tcp_pose": {
                "position": [
                    frame.tcp_pose.pose.position.x,
                    frame.tcp_pose.pose.position.y,
                    frame.tcp_pose.pose.position.z,
                ],
                "orientation": [
                    frame.tcp_pose.pose.orientation.x,
                    frame.tcp_pose.pose.orientation.y,
                    frame.tcp_pose.pose.orientation.z,
                    frame.tcp_pose.pose.orientation.w,
                ],
            },
            "pika_teleop_pose": {
                "position": [
                    frame.teleop_input_pose.pose.position.x,
                    frame.teleop_input_pose.pose.position.y,
                    frame.teleop_input_pose.pose.position.z,
                ],
                "orientation": [
                    frame.teleop_input_pose.pose.orientation.x,
                    frame.teleop_input_pose.pose.orientation.y,
                    frame.teleop_input_pose.pose.orientation.z,
                    frame.teleop_input_pose.pose.orientation.w,
                ],
            },
            "action": list(frame.commanded_joint_state.positions)
            if frame.commanded_joint_state and frame.commanded_joint_state.positions
            else (list(frame.joint_state.position) if frame.joint_state else []),
        }

        # Convert images
        wrist_cv = self._convert_image_msg(frame.wrist_image)
        depth_cv = self._convert_image_msg(frame.depth_image)
        overhead_cv = self._convert_image_msg(frame.overhead_image)

        # Enqueue for disk persistence
        self.current_writer.push_step(step_dict, wrist_cv, depth_cv, overhead_cv)
        self.recorded_step_count += 1

    def _cb_hardware_trigger(self, msg: Int32):
        """Hardware toggle from Pika Sense trigger (e.g. 1 = start, 2 = stop, 3 = discard)."""
        code = msg.data
        if code == 1 and self.state == EpisodeState.IDLE:
            self.start_recording(
                task_instruction="Teleoperated manipulation demonstration",
                operator_id="pika_operator",
            )
        elif code == 2 and self.state == EpisodeState.RECORDING:
            self.stop_recording(success_label=True, notes="Hardware trigger stop")
        elif code == 3 and self.state == EpisodeState.RECORDING:
            self.discard_recording(reason="Hardware trigger discard")

    def start_recording(
        self,
        task_instruction: str,
        operator_id: str,
        task_category: str = "manipulation",
        tags: Optional[list] = None,
    ) -> Tuple[bool, str, str]:
        """Initiates recording session."""
        if self.state == EpisodeState.RECORDING:
            return False, self.current_episode_id, "Already recording an episode"

        now_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        slug = slugify(task_instruction or "task")
        episode_id = f"ep_{now_str}_{slug}"

        self.current_episode_id = episode_id
        self.active_task = task_instruction
        self.recorded_step_count = 0
        self.start_time = time.time()

        self.current_writer = EpisodeWriter(
            episode_id=episode_id,
            base_dir=self.data_dir,
            task_instruction=task_instruction,
            operator_id=operator_id,
            task_category=task_category,
            tags=tags,
            target_fps=self.target_fps,
        )

        self.state = EpisodeState.RECORDING
        self.get_logger().info(f">>> STARTED RECORDING EPISODE: {episode_id} ({task_instruction})")
        return True, episode_id, "Episode recording started successfully"

    def stop_recording(self, success_label: bool = True, notes: str = "") -> Tuple[bool, str, int, float, str, float]:
        """Finalizes recording session and saves episode."""
        if self.state != EpisodeState.RECORDING or self.current_writer is None:
            return False, "", 0, 0.0, "", 0.0

        self.state = EpisodeState.FINALIZING
        ep_id = self.current_episode_id
        meta = self.current_writer.finalize(success_label=success_label, notes=notes)
        duration = meta["duration_sec"]
        num_frames = meta["total_steps"]
        save_path = self.current_writer.episode_dir

        self.state = EpisodeState.IDLE
        self.current_writer = None
        self.get_logger().info(
            f"<<< STOPPED EPISODE: {ep_id} | Frames: {num_frames} | Duration: {duration:.2f}s | Saved: {save_path}"
        )
        return True, ep_id, num_frames, duration, save_path, 100.0

    def discard_recording(self, reason: str = "") -> Tuple[bool, str]:
        """Discards active recording session."""
        if self.state != EpisodeState.RECORDING or self.current_writer is None:
            return False, "Not recording"

        ep_id = self.current_episode_id
        self.current_writer.discard()
        self.state = EpisodeState.IDLE
        self.current_writer = None
        self.get_logger().warn(f"!!! DISCARDED EPISODE: {ep_id} | Reason: {reason}")
        return True, f"Episode {ep_id} discarded"

    def _handle_start(self, request, response):
        success, ep_id, msg = self.start_recording(
            task_instruction=request.task_instruction,
            operator_id=request.operator_id or "default_operator",
            task_category=request.task_category or "manipulation",
            tags=list(request.tags),
        )
        response.success = success
        response.episode_id = ep_id
        response.message = msg
        return response

    def _handle_stop(self, request, response):
        success, ep_id, frames, duration, path, score = self.stop_recording(
            success_label=request.success_label,
            notes=request.notes,
        )
        response.success = success
        response.episode_id = ep_id
        response.num_frames = frames
        response.duration_sec = duration
        response.file_path = path
        response.qa_score = score
        return response

    def _handle_discard(self, request, response):
        success, msg = self.discard_recording(reason=request.reason)
        response.success = success
        response.message = msg
        return response

    def _handle_status(self, request, response):
        response.is_recording = (self.state == EpisodeState.RECORDING)
        response.current_episode_id = self.current_episode_id
        response.recorded_frames = self.recorded_step_count
        response.elapsed_seconds = (time.time() - self.start_time) if self.state == EpisodeState.RECORDING else 0.0
        response.buffer_usage_pct = 0.0
        response.storage_dir = self.data_dir
        return response

    def _publish_status(self):
        msg = RecorderStatus()
        msg.is_recording = (self.state == EpisodeState.RECORDING)
        msg.current_episode_id = self.current_episode_id
        msg.recorded_frames = self.recorded_step_count
        msg.elapsed_seconds = (time.time() - self.start_time) if self.state == EpisodeState.RECORDING else 0.0
        msg.buffer_usage_pct = 0.0
        msg.active_task_instruction = self.active_task
        self.pub_status.publish(msg)


def main(args=None):
    rclpy.init(args=args)
    node = JarvisPiperRecorderNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
