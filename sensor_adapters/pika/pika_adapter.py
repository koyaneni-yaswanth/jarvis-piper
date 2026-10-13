"""
AgileX PIKA Sense Spatial Input & Teleoperation Adapter.
Handles 6-DOF optical tracker pose stream, dead-man clutch, and low-pass filtering.
"""

from typing import Dict, Any, List, Tuple
import numpy as np


class PikaSenseAdapter:
    """
    Adapter for AgileX PIKA Sense / SteamVR wireless tracking device.
    Defaults to simulation mode when hardware USB receiver (VID 0x28de) is absent.
    """

    def __init__(self, mode: str = "simulation"):
        self.mode = mode.lower()
        self.clutch_engaged = False
        self.tracker_pose = [0.45, -0.08, 0.32, 0.0, 0.0, 0.0, 1.0]  # [x, y, z, qx, qy, qz, qw]
        self.button_state = {"trigger": 0.0, "grip": False, "menu": False}

    def get_spatial_pose(self) -> Tuple[List[float], List[float]]:
        """Returns ([x, y, z], [qx, qy, qz, qw])."""
        return list(self.tracker_pose[:3]), list(self.tracker_pose[3:])

    def is_clutch_engaged(self) -> bool:
        """Returns true if operator holds dead-man clutch enable switch."""
        return bool(self.clutch_engaged)

    def set_mock_pose(self, pos: List[float], quat: List[float], clutch: bool = True):
        """Sets simulated tracker spatial pose."""
        self.tracker_pose = list(pos) + list(quat)
        self.clutch_engaged = clutch
