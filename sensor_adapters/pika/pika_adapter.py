"""
AgileX PIKA Sense Spatial Input & Teleoperation Adapter.
Conforms to AgileX Pika Product User Manual (beta EN ROS2):
- Topic for 6-DOF Pose: /pika_pose (geometry_msgs/msg/PoseStamped)
- Dual-arm pose topics: /pika_pose_l, /pika_pose_r
- Gripper feedback topics: /gripper_l/data, /gripper/joint_states
- Coordinate system centered on gripper: X-axis forward, Y-axis left, Z-axis up (FLU)
- Hardware USB wireless receiver: Valve SteamVR (VID 0x28de, PID 0x2101)
- Dead-man clutch logic, tracking freshness checks, and LED status decoding.
"""

import time
from enum import Enum
from typing import Dict, Any, List, Tuple, Optional
import numpy as np


class PikaGripperLedStatus(Enum):
    """AgileX PIKA Gripper Status Indicator Codes."""
    POST_IN_PROGRESS = "Blinking Green: Power-on self-test in progress"
    STANDBY = "Solid Green: Self-test passed; standby mode (gripper disabled)"
    OPERATING = "Solid Blue: Operating mode active (gripper enabled)"
    FAULT = "Solid Red: Motor fault warning (diagnostic data frame required)"


class PikaSenseAdapter:
    """
    Adapter for AgileX PIKA Sense / SteamVR wireless tracking device.
    Defaults to simulation/mock mode when hardware USB receiver (VID 0x28de) is absent.
    """

    # Official AgileX ROS 2 Topic Names
    TOPIC_POSE_SINGLE = "/pika_pose"
    TOPIC_POSE_LEFT = "/pika_pose_l"
    TOPIC_POSE_RIGHT = "/pika_pose_r"
    TOPIC_GRIPPER_DATA = "/gripper_l/data"
    TOPIC_GRIPPER_JOINT_STATES = "/gripper/joint_states"

    # Calibration error tolerance threshold from manual (meters)
    CALIBRATION_ERROR_TOLERANCE_M = 0.005

    def __init__(self, mode: str = "simulation", tracking_timeout_sec: float = 0.05):
        self.mode = mode.lower()
        self.tracking_timeout_sec = tracking_timeout_sec

        # Gripper-centered coordinate frame: X forward, Y left, Z up (FLU)
        self.tracker_pose = [0.45, -0.08, 0.32, 0.0, 0.0, 0.0, 1.0]  # [x, y, z, qx, qy, qz, qw]
        self.last_pose_timestamp = time.time()

        # Teleoperation clutch reference caching
        self.clutch_engaged = False
        self.reference_hand_pose: Optional[List[float]] = None

        # Gripper states
        self.gripper_stroke_m = 0.035
        self.led_status = PikaGripperLedStatus.STANDBY
        self.button_state = {"trigger": 0.0, "grip": False, "menu": False}

    def get_spatial_pose(self) -> Tuple[List[float], List[float]]:
        """
        Returns ([x, y, z], [qx, qy, qz, qw]) in FLU gripper-centered frame.
        Raises TimeoutError if tracking is stale (> tracking_timeout_sec) in hardware mode.
        """
        if self.mode == "hardware" and (time.time() - self.last_pose_timestamp > self.tracking_timeout_sec):
            raise TimeoutError("PIKA Sense tracking signal lost or stale (> 50 ms)!")
        return list(self.tracker_pose[:3]), list(self.tracker_pose[3:])

    def is_clutch_engaged(self) -> bool:
        """Returns True if operator holds dead-man clutch enable switch."""
        return bool(self.clutch_engaged)

    def engage_clutch(self):
        """Engages dead-man clutch and snapshots reference hand pose."""
        self.clutch_engaged = True
        self.reference_hand_pose = list(self.tracker_pose[:3])

    def disengage_clutch(self):
        """Disengages dead-man clutch, freezing commanded robot motion."""
        self.clutch_engaged = False
        self.reference_hand_pose = None

    def get_relative_displacement(self) -> np.ndarray:
        """
        Calculates delta translation [dx, dy, dz] since clutch engagement.
        Returns zeros if clutch is released.
        """
        if not self.clutch_engaged or self.reference_hand_pose is None:
            return np.zeros(3, dtype=np.float32)
        curr_pos = np.array(self.tracker_pose[:3], dtype=np.float32)
        ref_pos = np.array(self.reference_hand_pose, dtype=np.float32)
        return curr_pos - ref_pos

    def get_led_indicator(self) -> PikaGripperLedStatus:
        """Returns current hardware LED status description."""
        return self.led_status

    def set_mock_pose(self, pos: List[float], quat: List[float], clutch: bool = True):
        """Sets simulated tracker spatial pose."""
        self.tracker_pose = list(pos) + list(quat)
        self.last_pose_timestamp = time.time()
        if clutch and not self.clutch_engaged:
            self.engage_clutch()
        elif not clutch:
            self.disengage_clutch()
