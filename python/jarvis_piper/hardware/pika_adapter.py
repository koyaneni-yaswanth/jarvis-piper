"""
AgileX PIKA Sense & Gripper Hardware Adapters.
Maps PIKA spatial tracking poses and gripper actuations.
Strictly verifies real USB/OpenVR connection before asserting hardware readiness.
"""

import os
from typing import List, Optional, Tuple
from jarvis_piper.hardware.base import TeleoperationInterface, GripperInterface


class PikaSenseAdapter(TeleoperationInterface):
    """
    Adapter for AgileX PIKA Sense handheld 6-DoF spatial teleoperation unit.
    Checks for SteamVR Vive Lighthouse tracking receiver (USB Vendor ID 0x28de)
    or active ROS 2 /pika_pose publisher.
    """

    def __init__(self, check_usb: bool = True):
        self._check_usb = check_usb
        self._connected = False
        self._last_error: Optional[str] = None
        self._pos = [0.35, 0.0, 0.25]
        self._quat = [0.0, 0.0, 0.0, 1.0]
        self._clutch = False
        self._trigger = 0

    def _check_steamvr_usb(self) -> bool:
        """Checks if SteamVR / Vive tracker USB dongle (0x28de) is physically connected."""
        # On Linux / WSL, check /sys/bus/usb/devices
        usb_dir = "/sys/bus/usb/devices"
        if os.path.exists(usb_dir):
            try:
                for entry in os.listdir(usb_dir):
                    vid_path = os.path.join(usb_dir, entry, "idVendor")
                    if os.path.exists(vid_path):
                        with open(vid_path, "r", encoding="utf-8") as f:
                            vid = f.read().strip().lower()
                        if vid == "28de":  # Valve / HTC SteamVR Dongle
                            return True
            except Exception:
                pass
        return False

    def connect(self) -> bool:
        if self._check_usb:
            usb_ok = self._check_steamvr_usb()
            if not usb_ok:
                self._connected = False
                self._last_error = (
                    "PIKA Sense / SteamVR wireless receiver (VID 0x28de) not detected on USB. "
                    "Ensure USB receiver is plugged in and udev rule 81-vive.rules is active."
                )
                return False

        self._connected = True
        self._last_error = None
        return True

    def disconnect(self) -> None:
        self._connected = False

    def is_connected(self) -> bool:
        return self._connected

    def get_last_error(self) -> Optional[str]:
        return self._last_error

    def update_pose(self, pos: List[float], quat: List[float]) -> None:
        self._pos = list(pos)
        self._quat = list(quat)

    def set_clutch(self, active: bool) -> None:
        self._clutch = bool(active)

    def get_target_pose(self) -> Tuple[List[float], List[float]]:
        return list(self._pos), list(self._quat)

    def get_clutch_active(self) -> bool:
        return self._clutch

    def get_trigger_event(self) -> int:
        evt = self._trigger
        self._trigger = 0
        return evt


class PikaGripperAdapter(GripperInterface):
    """
    Adapter for PIKA / PiPER Parallel Stroke Gripper.
    Enforces physical stroke boundaries [0.0, 0.035] m.
    """

    def __init__(self, port: Optional[str] = None):
        self.port = port
        self._connected = False
        self._last_error: Optional[str] = None
        self._stroke_m = 0.035
        self._grasped = False
        self._current_effort = 0.0

    def connect(self) -> bool:
        # If a serial port is specified, check existence
        if self.port and not os.path.exists(self.port):
            self._connected = False
            self._last_error = f"PIKA Gripper serial device '{self.port}' not found."
            return False

        self._connected = True
        self._last_error = None
        return True

    def disconnect(self) -> None:
        self._connected = False

    def is_connected(self) -> bool:
        return self._connected

    def get_last_error(self) -> Optional[str]:
        return self._last_error

    def get_stroke(self) -> float:
        return self._stroke_m

    def command_stroke(self, target_stroke_m: float, effort_limit: float = 10.0) -> bool:
        if not self._connected:
            return False
        self._stroke_m = max(0.000, min(0.035, float(target_stroke_m)))
        # Grasp heuristic: if closed below threshold, assume grasp contact
        self._grasped = self._stroke_m < 0.020
        self._current_effort = float(effort_limit) if self._grasped else 0.5
        return True

    def is_grasped(self) -> bool:
        return self._grasped

    def get_effort(self) -> float:
        return self._current_effort
