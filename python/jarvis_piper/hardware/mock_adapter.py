"""
High-Fidelity Mock Adapters for JARVIS-PiPER.
Generates realistic multi-modal kinematics, camera feeds, and gripper motions without hardware.
"""

import math
import time
from typing import Any, Dict, List, Optional, Tuple
import cv2
import numpy as np

from jarvis_piper.hardware.base import (
    RobotInterface,
    CameraInterface,
    GripperInterface,
    TeleoperationInterface,
)


class MockPiperAdapter(RobotInterface):
    """Synthetic 6-DOF PiPER arm emulator."""

    def __init__(self):
        self._connected = True
        self._start_t = time.time()
        self._last_cmd: Optional[List[float]] = None

    def connect(self) -> bool:
        self._connected = True
        return True

    def disconnect(self) -> None:
        self._connected = False

    def is_connected(self) -> bool:
        return self._connected

    def get_joint_states(self) -> Tuple[List[float], List[float], List[float]]:
        t = time.time() - self._start_t
        if self._last_cmd is not None:
            return self._last_cmd, [0.0] * 6, [0.0] * 6

        q1 = 0.5 * math.sin(0.4 * t)
        q2 = -0.4 + 0.3 * math.cos(0.5 * t)
        q3 = 0.8 + 0.2 * math.sin(0.3 * t)
        q4 = 0.2 * math.sin(0.5 * t)
        q5 = -0.4 + 0.2 * math.cos(0.4 * t)
        q6 = 0.3 * math.sin(0.6 * t)

        v = [
            0.2 * math.cos(0.4 * t),
            -0.15 * math.sin(0.5 * t),
            0.06 * math.cos(0.3 * t),
            0.1 * math.cos(0.5 * t),
            -0.08 * math.sin(0.4 * t),
            0.18 * math.cos(0.6 * t),
        ]
        eff = [0.0] * 6
        return [q1, q2, q3, q4, q5, q6], v, eff

    def get_tcp_pose(self) -> Tuple[List[float], List[float]]:
        t = time.time() - self._start_t
        x = 0.35 + 0.1 * math.cos(0.3 * t)
        y = 0.15 * math.sin(0.4 * t)
        z = 0.25 + 0.08 * math.sin(0.2 * t)
        return [x, y, z], [0.0, 0.0, 0.0, 1.0]

    def send_joint_command(self, target_positions_rad: List[float]) -> bool:
        self._last_cmd = list(target_positions_rad)
        return True

    def command_joint_position(self, target_positions_rad: List[float]) -> bool:
        return self.send_joint_command(target_positions_rad)


class MockCameraAdapter(CameraInterface):
    """Synthetic RGB and Depth image generator."""

    def __init__(self, width: int = 640, height: int = 480):
        self.width = width
        self.height = height
        self._connected = True
        self._start_t = time.time()

    def connect(self) -> bool:
        self._connected = True
        return True

    def disconnect(self) -> None:
        self._connected = False

    def is_connected(self) -> bool:
        return self._connected

    def get_rgb_frame(self) -> Optional[np.ndarray]:
        t = time.time() - self._start_t
        img = np.zeros((self.height, self.width, 3), dtype=np.uint8)
        img[:] = (45, 50, 58)  # Tabletop background

        # Grid lines
        for y in range(100, self.height, 100):
            cv2.line(img, (0, y), (self.width, y), (60, 65, 75), 1)

        # Simulated Target Cube
        cx = int(self.width / 2 + 100 * math.sin(0.3 * t))
        cy = int(self.height / 2 + 50 * math.cos(0.4 * t))
        cv2.rectangle(img, (cx - 30, cy - 30), (cx + 30, cy + 30), (35, 35, 220), -1)
        cv2.rectangle(img, (cx - 30, cy - 30), (cx + 30, cy + 30), (240, 240, 240), 2)

        # Overlay text
        cv2.putText(img, f"JARVIS MOCK CAM | T={t:.2f}s", (20, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (220, 220, 220), 2)
        return img

    def get_depth_frame(self) -> Optional[np.ndarray]:
        t = time.time() - self._start_t
        depth = np.full((self.height, self.width), fill_value=1200, dtype=np.uint16)
        cx = int(self.width / 2 + 100 * math.sin(0.3 * t))
        cy = int(self.height / 2 + 50 * math.cos(0.4 * t))
        depth[max(0, cy - 30) : min(self.height, cy + 30), max(0, cx - 30) : min(self.width, cx + 30)] = 800
        return depth

    def get_intrinsics(self) -> Dict[str, Any]:
        return {
            "fx": 525.0,
            "fy": 525.0,
            "cx": self.width / 2.0,
            "cy": self.height / 2.0,
            "width": self.width,
            "height": self.height,
        }


class MockGripperAdapter(GripperInterface):
    """Synthetic parallel gripper emulator."""

    def __init__(self, stroke_max: float = 0.035):
        self.stroke_max = stroke_max
        self._connected = True
        self._start_t = time.time()
        self._current_stroke = 0.020

    def connect(self) -> bool:
        self._connected = True
        return True

    def disconnect(self) -> None:
        self._connected = False

    def is_connected(self) -> bool:
        return self._connected

    def get_stroke(self) -> float:
        return self._current_stroke

    def command_stroke(self, target_stroke_m: float) -> bool:
        self._current_stroke = max(0.0, min(self.stroke_max, float(target_stroke_m)))
        return True

    def is_grasped(self) -> bool:
        return self.get_stroke() < 0.012


class MockPikaSenseAdapter(TeleoperationInterface):
    """Synthetic PIKA Sense optical tracking controller."""

    def __init__(self):
        self._connected = True
        self._start_t = time.time()

    def connect(self) -> bool:
        self._connected = True
        return True

    def disconnect(self) -> None:
        self._connected = False

    def is_connected(self) -> bool:
        return self._connected

    def get_target_pose(self) -> Tuple[List[float], List[float]]:
        t = time.time() - self._start_t
        pos = [0.35 + 0.1 * math.cos(0.3 * t), 0.15 * math.sin(0.4 * t), 0.25 + 0.08 * math.sin(0.2 * t)]
        quat = [0.0, 0.0, 0.0, 1.0]
        return pos, quat

    def get_master_pose(self) -> Tuple[List[float], List[float]]:
        return self.get_target_pose()

    def get_trigger_stroke(self) -> float:
        t = time.time() - self._start_t
        return 0.5 + 0.5 * math.sin(0.3 * t)

    def get_button_state(self, button_name: str) -> bool:
        return False

    def get_clutch_active(self) -> bool:
        return True

    def get_trigger_event(self) -> int:
        return 0
