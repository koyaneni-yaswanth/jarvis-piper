#!/usr/bin/env python3
"""
JARVIS PiPER Time Synchronizer Node
Aligns multi-modal sensory streams (RGB, Depth, JointState, Gripper, Pika Pose, TF, IMU)
into a unified, deterministic, synchronized observation stream at target frequency.
"""

import math
import sys
import time
from typing import Optional

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy
from builtin_interfaces.msg import Time as MsgTime
from sensor_msgs.msg import JointState, Image, Imu
from geometry_msgs.msg import PoseStamped, TransformStamped
from trajectory_msgs.msg import JointTrajectoryPoint
from tf2_ros import Buffer, TransformListener, TransformException
from std_msgs.msg import Float32

from jarvis_piper_interfaces.msg import SynchronizedFrame
from jarvis_piper_sync.ring_buffer import TemporalRingBuffer


def msg_time_to_seconds(stamp: MsgTime) -> float:
    return stamp.sec + stamp.nanosec * 1e-9


class JarvisPiperTimeSynchronizer(Node):
    """Core Time Synchronizer Node for embodied AI data capture."""

    def __init__(self):
        super().__init__("jarvis_piper_time_synchronizer")

        # Declare configurable parameters
        self.declare_parameter("target_rate_hz", 30.0)
        self.declare_parameter("slop_window_ms", 35.0)
        self.declare_parameter("camera_rgb_topic", "/camera")
        self.declare_parameter("camera_depth_topic", "/camera/depth_image")
        self.declare_parameter("overhead_rgb_topic", "/overhead_camera/color/image_raw")
        self.declare_parameter("joint_states_topic", "/joint_states")
        self.declare_parameter("gripper_ctrl_topic", "/gripper/ctrl")
        self.declare_parameter("pika_pose_topic", "/pika_pose")
        self.declare_parameter("imu_topic", "/imu")
        self.declare_parameter("base_frame", "base_link")
        self.declare_parameter("tcp_frame", "piper_gripper_base")
        self.declare_parameter("sync_topic", "/jarvis_piper/sync_frame")

        self.target_rate_hz = self.get_parameter("target_rate_hz").value
        self.slop_sec = self.get_parameter("slop_window_ms").value / 1000.0
        self.base_frame = self.get_parameter("base_frame").value
        self.tcp_frame = self.get_parameter("tcp_frame").value

        self.get_logger().info(
            f"Initializing Time Synchronizer at {self.target_rate_hz} Hz (Slop: {self.slop_sec*1000:.1f}ms)"
        )

        # Buffers
        self.rgb_buffer = TemporalRingBuffer(capacity=300)
        self.depth_buffer = TemporalRingBuffer(capacity=300)
        self.overhead_buffer = TemporalRingBuffer(capacity=300)
        self.joints_buffer = TemporalRingBuffer(capacity=1000)
        self.gripper_buffer = TemporalRingBuffer(capacity=1000)
        self.teleop_buffer = TemporalRingBuffer(capacity=1000)
        self.imu_buffer = TemporalRingBuffer(capacity=1000)

        # QoS for sensor streams
        sensor_qos = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            history=HistoryPolicy.KEEP_LAST,
            depth=10,
        )
        reliable_qos = QoSProfile(
            reliability=ReliabilityPolicy.RELIABLE,
            history=HistoryPolicy.KEEP_LAST,
            depth=10,
        )

        # Subscriptions
        self.sub_rgb = self.create_subscription(
            Image, self.get_parameter("camera_rgb_topic").value, self._cb_rgb, sensor_qos
        )
        self.sub_depth = self.create_subscription(
            Image, self.get_parameter("camera_depth_topic").value, self._cb_depth, sensor_qos
        )
        self.sub_overhead = self.create_subscription(
            Image, self.get_parameter("overhead_rgb_topic").value, self._cb_overhead, sensor_qos
        )
        self.sub_joints = self.create_subscription(
            JointState, self.get_parameter("joint_states_topic").value, self._cb_joints, reliable_qos
        )
        self.sub_gripper = self.create_subscription(
            Float32, self.get_parameter("gripper_ctrl_topic").value, self._cb_gripper, reliable_qos
        )
        self.sub_teleop = self.create_subscription(
            PoseStamped, self.get_parameter("pika_pose_topic").value, self._cb_teleop, reliable_qos
        )
        self.sub_imu = self.create_subscription(
            Imu, self.get_parameter("imu_topic").value, self._cb_imu, sensor_qos
        )

        # TF2 Buffer & Listener
        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self)

        # Publisher
        self.pub_sync = self.create_publisher(
            SynchronizedFrame, self.get_parameter("sync_topic").value, 10
        )

        # State tracking
        self.step_index = 0
        self.last_sync_time = 0.0
        self.published_count = 0
        self.sync_jitters = []

        # Synchronization Timer
        timer_period = 1.0 / max(1.0, self.target_rate_hz)
        self.sync_timer = self.create_timer(timer_period, self._sync_step)

    def _cb_rgb(self, msg: Image):
        t = msg_time_to_seconds(msg.header.stamp)
        if t == 0.0:
            t = self.get_clock().now().nanoseconds * 1e-9
        self.rgb_buffer.push(t, msg)

    def _cb_depth(self, msg: Image):
        t = msg_time_to_seconds(msg.header.stamp)
        if t == 0.0:
            t = self.get_clock().now().nanoseconds * 1e-9
        self.depth_buffer.push(t, msg)

    def _cb_overhead(self, msg: Image):
        t = msg_time_to_seconds(msg.header.stamp)
        if t == 0.0:
            t = self.get_clock().now().nanoseconds * 1e-9
        self.overhead_buffer.push(t, msg)

    def _cb_joints(self, msg: JointState):
        t = msg_time_to_seconds(msg.header.stamp)
        if t == 0.0:
            t = self.get_clock().now().nanoseconds * 1e-9
        self.joints_buffer.push(t, msg)

    def _cb_gripper(self, msg: Float32):
        t = self.get_clock().now().nanoseconds * 1e-9
        self.gripper_buffer.push(t, msg.data)

    def _cb_teleop(self, msg: PoseStamped):
        t = msg_time_to_seconds(msg.header.stamp)
        if t == 0.0:
            t = self.get_clock().now().nanoseconds * 1e-9
        self.teleop_buffer.push(t, msg)

    def _cb_imu(self, msg: Imu):
        t = msg_time_to_seconds(msg.header.stamp)
        if t == 0.0:
            t = self.get_clock().now().nanoseconds * 1e-9
        self.imu_buffer.push(t, msg)

    def _query_tcp_pose(self) -> Optional[PoseStamped]:
        """Resolves end-effector TCP pose in base_frame."""
        try:
            tf: TransformStamped = self.tf_buffer.lookup_transform(
                self.base_frame, self.tcp_frame, rclpy.time.Time()
            )
            p = PoseStamped()
            p.header = tf.header
            p.pose.position.x = tf.transform.translation.x
            p.pose.position.y = tf.transform.translation.y
            p.pose.position.z = tf.transform.translation.z
            p.pose.orientation = tf.transform.rotation
            return p
        except TransformException:
            # Fallback if TF is uninitialized
            return None

    def _sync_step(self):
        """Timer callback performing temporal alignment across buffers."""
        now_msg = self.get_clock().now().to_msg()
        target_t = msg_time_to_seconds(now_msg)

        # 1. Joint state is primary physical ground truth
        latest_joint, jt_diff = self.joints_buffer.get_nearest(target_t, self.slop_sec * 2.0)
        if latest_joint is None:
            latest_joint, _ = self.joints_buffer.get_latest()

        if latest_joint is None:
            # Wait until robot state stream arrives
            return

        # Use joint timestamp or current target time
        sync_t = target_t

        # 2. Query other modalities
        rgb_img, _ = self.rgb_buffer.get_nearest(sync_t, self.slop_sec)
        depth_img, _ = self.depth_buffer.get_nearest(sync_t, self.slop_sec)
        overhead_img, _ = self.overhead_buffer.get_nearest(sync_t, self.slop_sec)
        teleop_pose, _ = self.teleop_buffer.get_nearest(sync_t, self.slop_sec)
        imu_msg, _ = self.imu_buffer.get_nearest(sync_t, self.slop_sec)
        gripper_val, _ = self.gripper_buffer.get_nearest(sync_t, self.slop_sec * 3.0)

        # If gripper topic has no explicit Float32, check joint_states for finger joints
        gripper_pos = 0.0
        gripper_vel = 0.0
        gripper_eff = 0.0

        if latest_joint is not None:
            for name, pos in zip(latest_joint.name, latest_joint.position):
                if "finger" in name or "gripper" in name:
                    gripper_pos = float(pos)
                    break
            if gripper_val is not None:
                gripper_pos = float(gripper_val)

        # Query TCP Pose from TF
        tcp_pose = self._query_tcp_pose()
        if tcp_pose is None:
            tcp_pose = PoseStamped()
            tcp_pose.header.stamp = now_msg
            tcp_pose.header.frame_id = self.base_frame

        if teleop_pose is None:
            teleop_pose = PoseStamped()
            teleop_pose.header.stamp = now_msg
            teleop_pose.header.frame_id = self.base_frame

        if imu_msg is None:
            imu_msg = Imu()
            imu_msg.header.stamp = now_msg
            imu_msg.header.frame_id = self.base_frame

        if rgb_img is None:
            rgb_img = Image()
            rgb_img.header.stamp = now_msg

        if depth_img is None:
            depth_img = Image()
            depth_img.header.stamp = now_msg

        if overhead_img is None:
            overhead_img = Image()
            overhead_img.header.stamp = now_msg

        # Assemble SynchronizedFrame
        frame = SynchronizedFrame()
        frame.timestamp = now_msg
        frame.step_index = self.step_index
        frame.joint_state = latest_joint
        frame.gripper_position = gripper_pos
        frame.gripper_velocity = gripper_vel
        frame.gripper_effort = gripper_eff
        frame.tcp_pose = tcp_pose
        frame.teleop_input_pose = teleop_pose
        frame.wrist_image = rgb_img
        frame.overhead_image = overhead_img
        frame.depth_image = depth_img
        frame.imu_data = imu_msg

        # Action: commanded joint target or teleop delta
        cmd_pt = JointTrajectoryPoint()
        if latest_joint is not None:
            cmd_pt.positions = list(latest_joint.position)
        frame.commanded_joint_state = cmd_pt

        # Publish
        self.pub_sync.publish(frame)
        self.step_index += 1
        self.published_count += 1

        if self.last_sync_time > 0:
            dt = sync_t - self.last_sync_time
            jitter = abs(dt - (1.0 / self.target_rate_hz)) * 1000.0
            self.sync_jitters.append(jitter)
            if len(self.sync_jitters) > 100:
                self.sync_jitters.pop(0)

        self.last_sync_time = sync_t


def main(args=None):
    rclpy.init(args=args)
    node = JarvisPiperTimeSynchronizer()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
