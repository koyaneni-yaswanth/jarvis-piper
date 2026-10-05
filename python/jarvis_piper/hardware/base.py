"""
Hardware Abstraction Layer (HAL) Base Interfaces.
Defines clean abstract interfaces for robots, grippers, cameras, and teleoperators.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple
import numpy as np


class HardwareInterface(ABC):
    """Root interface for all physical and mock hardware components."""

    @abstractmethod
    def connect(self) -> bool:
        """Establishes connection to the hardware device or simulator."""
        pass

    @abstractmethod
    def disconnect(self) -> None:
        """Safely disconnects or releases hardware resources."""
        pass

    @abstractmethod
    def is_connected(self) -> bool:
        """Returns True if hardware communication is active."""
        pass


class RobotInterface(HardwareInterface):
    """Abstract interface for 6-DOF / N-DOF robotic manipulators."""

    @abstractmethod
    def get_joint_states(self) -> Tuple[List[float], List[float], List[float]]:
        """Returns (positions_rad, velocities_rad_s, efforts_nm)."""
        pass

    @abstractmethod
    def get_tcp_pose(self) -> Tuple[List[float], List[float]]:
        """Returns (position_xyz_m, orientation_xyzw_quat)."""
        pass

    @abstractmethod
    def send_joint_command(self, target_positions_rad: List[float]) -> bool:
        """Commands target joint positions."""
        pass


class GripperInterface(HardwareInterface):
    """Abstract interface for robotic end-effector grippers."""

    @abstractmethod
    def get_stroke(self) -> float:
        """Returns current gripper finger opening stroke in meters."""
        pass

    @abstractmethod
    def command_stroke(self, target_stroke_m: float) -> bool:
        """Commands target gripper stroke in meters."""
        pass

    @abstractmethod
    def is_grasped(self) -> bool:
        """Returns True if object contact is detected."""
        pass


class CameraInterface(HardwareInterface):
    """Abstract interface for RGB and Depth perception sensors."""

    @abstractmethod
    def get_rgb_frame(self) -> Optional[np.ndarray]:
        """Returns HxWx3 uint8 BGR/RGB numpy image frame."""
        pass

    @abstractmethod
    def get_depth_frame(self) -> Optional[np.ndarray]:
        """Returns HxW uint16 millimeter depth map."""
        pass

    @abstractmethod
    def get_intrinsics(self) -> Dict[str, Any]:
        """Returns camera intrinsic parameters (fx, fy, cx, cy, resolution)."""
        pass


class TeleoperationInterface(HardwareInterface):
    """Abstract interface for spatial tracking controllers (e.g. PIKA Sense)."""

    @abstractmethod
    def get_target_pose(self) -> Tuple[List[float], List[float]]:
        """Returns commanded (position_xyz_m, orientation_xyzw_quat)."""
        pass

    @abstractmethod
    def get_clutch_active(self) -> bool:
        """Returns True if teleoperation clutch / dead-man switch is held."""
        pass

    @abstractmethod
    def get_trigger_event(self) -> int:
        """Returns trigger event code (0=none, 1=start, 2=stop, 3=discard)."""
        pass
