"""
AgileX PIKA Sense & Gripper Hardware Adapters.
Maps PIKA spatial tracking poses and gripper actuations.
"""

from typing import List, Tuple
from jarvis_piper.hardware.base import TeleoperationInterface, GripperInterface


class PikaSenseAdapter(TeleoperationInterface):
    """Adapter for AgileX PIKA Sense handheld 6-DoF spatial teleoperation unit."""

    def __init__(self):
        self._connected = True
        self._pos = [0.35, 0.0, 0.25]
        self._quat = [0.0, 0.0, 0.0, 1.0]
        self._clutch = True
        self._trigger = 0

    def connect(self) -> bool:
        self._connected = True
        return True

    def disconnect(self) -> None:
        self._connected = False

    def is_connected(self) -> bool:
        return self._connected

    def update_pose(self, pos: List[float], quat: List[float]) -> None:
        self._pos = list(pos)
        self._quat = list(quat)

    def get_target_pose(self) -> Tuple[List[float], List[float]]:
        return list(self._pos), list(self._quat)

    def get_clutch_active(self) -> bool:
        return self._clutch

    def get_trigger_event(self) -> int:
        evt = self._trigger
        self._trigger = 0
        return evt


class PikaGripperAdapter(GripperInterface):
    """Adapter for PIKA / PiPER Parallel Stroke Gripper."""

    def __init__(self):
        self._connected = True
        self._stroke_m = 0.035
        self._grasped = False

    def connect(self) -> bool:
        self._connected = True
        return True

    def disconnect(self) -> None:
        self._connected = False

    def is_connected(self) -> bool:
        return self._connected

    def get_stroke(self) -> float:
        return self._stroke_m

    def command_stroke(self, target_stroke_m: float) -> bool:
        if not self._connected:
            return False
        self._stroke_m = max(0.000, min(0.035, float(target_stroke_m)))
        self._grasped = self._stroke_m < 0.015
        return True

    def is_grasped(self) -> bool:
        return self._grasped
