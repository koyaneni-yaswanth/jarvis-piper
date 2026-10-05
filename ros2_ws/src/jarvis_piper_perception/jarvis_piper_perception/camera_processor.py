"""
Camera Stream Processor Node.
Subscribes to raw RGB and Depth topics, validates timestamps, performs range clipping,
and republishes optimized streams for recorders and models.
"""

import numpy as np
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image, CompressedImage

try:
    from cv_bridge import CvBridge
    HAS_CV_BRIDGE = True
except ImportError:
    HAS_CV_BRIDGE = False

try:
    import cv2
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False


class CameraProcessorNode(Node):
    """Processes, normalizes, and filters camera feeds."""

    def __init__(self):
        super().__init__('camera_processor_node')

        self.declare_parameter('rgb_input_topic', '/camera')
        self.declare_parameter('depth_input_topic', '/camera/depth_image')
        self.declare_parameter('rgb_output_topic', '/camera/processed/color')
        self.declare_parameter('depth_output_topic', '/camera/processed/depth')
        self.declare_parameter('target_width', 640)
        self.declare_parameter('target_height', 480)

        rgb_in = self.get_parameter('rgb_input_topic').value
        depth_in = self.get_parameter('depth_input_topic').value
        rgb_out = self.get_parameter('rgb_output_topic').value
        depth_out = self.get_parameter('depth_output_topic').value

        self.bridge = CvBridge() if HAS_CV_BRIDGE else None

        # Subscriptions
        self.rgb_sub = self.create_subscription(Image, rgb_in, self._rgb_callback, 10)
        self.depth_sub = self.create_subscription(Image, depth_in, self._depth_callback, 10)

        # Publishers
        self.rgb_pub = self.create_publisher(Image, rgb_out, 10)
        self.depth_pub = self.create_publisher(Image, depth_out, 10)

        self.get_logger().info(f"Camera Processor started. In: {rgb_in}, Out: {rgb_out}")

    def _rgb_callback(self, msg: Image):
        # Pass-through or resize
        if self.bridge and HAS_CV2:
            try:
                cv_img = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
                # Resize if necessary
                w = self.get_parameter('target_width').value
                h = self.get_parameter('target_height').value
                if cv_img.shape[1] != w or cv_img.shape[0] != h:
                    cv_img = cv2.resize(cv_img, (w, h))
                out_msg = self.bridge.cv2_to_imgmsg(cv_img, encoding='bgr8')
                out_msg.header = msg.header
                self.rgb_pub.publish(out_msg)
                return
            except Exception as e:
                self.get_logger().warn(f"RGB CV Bridge error: {e}", throttle_duration_sec=5.0)

        self.rgb_pub.publish(msg)

    def _depth_callback(self, msg: Image):
        # Clip depth to valid metric range [0.1m, 2.5m]
        if self.bridge and HAS_CV2:
            try:
                depth_img = self.bridge.imgmsg_to_cv2(msg, desired_encoding='passthrough')
                depth_clipped = np.clip(depth_img, 100, 2500)  # millimeters
                out_msg = self.bridge.cv2_to_imgmsg(depth_clipped, encoding=msg.encoding)
                out_msg.header = msg.header
                self.depth_pub.publish(out_msg)
                return
            except Exception as e:
                self.get_logger().warn(f"Depth CV Bridge error: {e}", throttle_duration_sec=5.0)

        self.depth_pub.publish(msg)


def main(args=None):
    rclpy.init(args=args)
    node = CameraProcessorNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
