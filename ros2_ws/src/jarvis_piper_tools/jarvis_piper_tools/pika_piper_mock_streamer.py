"""
High-Fidelity Simulated Hardware & Telemetry Streamer for PIKA PiPER.
Emits realistic 6-DOF PiPER arm trajectories, parallel gripper strokes, Pika Sense poses,
synthetic RGB/Depth camera frames, and dynamic TF broadcasts.
"""

import math
import sys
import time

import cv2
import numpy as np
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState, Image, Imu
from geometry_msgs.msg import PoseStamped, TransformStamped
from std_msgs.msg import Float32
from tf2_ros import TransformBroadcaster
from cv_bridge import CvBridge

PIPER_JOINTS = [
    "piper_joint1",
    "piper_joint2",
    "piper_joint3",
    "piper_joint4",
    "piper_joint5",
    "piper_joint6",
    "piper_finger_left_joint",
    "piper_finger_right_joint",
]


class PikaPiperMockStreamer(Node):
    """High-fidelity simulated hardware emitter."""

    def __init__(self):
        super().__init__("pika_piper_mock_streamer")

        self.declare_parameter("publish_rate_hz", 30.0)
        self.rate_hz = self.get_parameter("publish_rate_hz").value

        self.pub_joints = self.create_publisher(JointState, "/joint_states", 10)
        self.pub_pika = self.create_publisher(PoseStamped, "/pika_pose", 10)
        self.pub_gripper = self.create_publisher(Float32, "/gripper/ctrl", 10)
        self.pub_rgb = self.create_publisher(Image, "/camera", 10)
        self.pub_depth = self.create_publisher(Image, "/camera/depth_image", 10)
        self.pub_imu = self.create_publisher(Imu, "/imu", 10)

        self.tf_broadcaster = TransformBroadcaster(self)
        self.bridge = CvBridge()

        self.start_time = time.time()
        self.timer = self.create_timer(1.0 / self.rate_hz, self._tick)
        self.get_logger().info(f"Pika PiPER Mock Hardware Streamer running at {self.rate_hz} Hz")

    def _tick(self):
        now_msg = self.get_clock().now().to_msg()
        t = time.time() - self.start_time

        # Smooth pick-and-place periodic joint trajectory
        q1 = 0.5 * math.sin(0.4 * t)
        q2 = -0.4 + 0.3 * math.cos(0.5 * t)
        q3 = 0.8 + 0.2 * math.sin(0.3 * t)
        q4 = 0.2 * math.sin(0.5 * t)
        q5 = -0.4 + 0.2 * math.cos(0.4 * t)
        q6 = 0.3 * math.sin(0.6 * t)

        # Gripper stroke periodic open/close (0.005 to 0.035 m)
        stroke = 0.020 + 0.015 * math.sin(0.2 * t)

        # 1. JointState
        js = JointState()
        js.header.stamp = now_msg
        js.name = PIPER_JOINTS
        js.position = [q1, q2, q3, q4, q5, q6, stroke, stroke]
        js.velocity = [
            0.2 * math.cos(0.4 * t),
            -0.15 * math.sin(0.5 * t),
            0.06 * math.cos(0.3 * t),
            0.1 * math.cos(0.5 * t),
            -0.08 * math.sin(0.4 * t),
            0.18 * math.cos(0.6 * t),
            0.003 * math.cos(0.2 * t),
            0.003 * math.cos(0.2 * t),
        ]
        js.effort = [0.0] * 8
        self.pub_joints.publish(js)

        # 2. Pika Teleop Pose
        pika = PoseStamped()
        pika.header.stamp = now_msg
        pika.header.frame_id = "base_link"
        pika.pose.position.x = 0.35 + 0.1 * math.cos(0.3 * t)
        pika.pose.position.y = 0.15 * math.sin(0.4 * t)
        pika.pose.position.z = 0.25 + 0.08 * math.sin(0.2 * t)
        pika.pose.orientation.w = 1.0
        self.pub_pika.publish(pika)

        # 3. Gripper Control
        g_msg = Float32()
        g_msg.data = float(stroke)
        self.pub_gripper.publish(g_msg)

        # 4. IMU
        imu = Imu()
        imu.header.stamp = now_msg
        imu.header.frame_id = "base_link"
        imu.linear_acceleration.z = 9.81
        self.pub_imu.publish(imu)

        # 5. Dynamic TF Broadcast (base_link -> piper_gripper_base)
        tf_msg = TransformStamped()
        tf_msg.header.stamp = now_msg
        tf_msg.header.frame_id = "base_link"
        tf_msg.child_frame_id = "piper_gripper_base"
        tf_msg.transform.translation.x = pika.pose.position.x
        tf_msg.transform.translation.y = pika.pose.position.y
        tf_msg.transform.translation.z = pika.pose.position.z
        tf_msg.transform.rotation.w = 1.0
        self.tf_broadcaster.sendTransform(tf_msg)

        # 6. Synthetic RGB & Depth Frames
        # Render a 480x640 workspace image with moving block
        rgb_canvas = np.zeros((480, 640, 3), dtype=np.uint8)
        rgb_canvas[:] = (40, 45, 52)  # Dark tabletop

        # Table boundary grid
        cv2.line(rgb_canvas, (100, 380), (540, 380), (70, 75, 85), 2)
        cv2.putText(
            rgb_canvas,
            f"JARVIS PiPER Sim Cam | T={t:.1f}s",
            (20, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (220, 220, 220),
            2,
        )

        # Target manipulation object (red cube)
        cx = int(320 + 80 * math.sin(0.3 * t))
        cy = int(240 + 40 * math.cos(0.4 * t))
        cv2.rectangle(rgb_canvas, (cx - 25, cy - 25), (cx + 25, cy + 25), (30, 30, 220), -1)
        cv2.rectangle(rgb_canvas, (cx - 25, cy - 25), (cx + 25, cy + 25), (255, 255, 255), 2)

        # Gripper fingers overlay
        cv2.line(rgb_canvas, (cx - 35, cy - 40), (cx - 35, cy + 10), (0, 255, 255), 4)
        cv2.line(rgb_canvas, (cx + 35, cy - 40), (cx + 35, cy + 10), (0, 255, 255), 4)

        img_msg = self.bridge.cv2_to_imgmsg(rgb_canvas, encoding="bgr8")
        img_msg.header.stamp = now_msg
        img_msg.header.frame_id = "camera_color_optical_frame"
        self.pub_rgb.publish(img_msg)

        # Synthetic 16-bit millimeter depth map
        depth_canvas = np.full((480, 640), fill_value=1200, dtype=np.uint16)
        depth_canvas[cy - 25 : cy + 25, cx - 25 : cx + 25] = 750  # Object closer
        depth_msg = self.bridge.cv2_to_imgmsg(depth_canvas, encoding="16UC1")
        depth_msg.header.stamp = now_msg
        depth_msg.header.frame_id = "camera_depth_optical_frame"
        self.pub_depth.publish(depth_msg)


def main(args=None):
    rclpy.init(args=args)
    node = PikaPiperMockStreamer()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
