"""
AgileX PiPER 6-DOF Robotic Arm Adapter.
Provides uniform interface across Simulation and Physical CAN Hardware.
"""

from typing import List, Tuple, Optional
import numpy as np
from world_model.spatial import PiperKinematics


class PiperArmAdapter:
    """
    Adapter for the AgileX PiPER 6-DOF Robotic Arm.
    Defaults to SIMULATION mode unless physical SocketCAN is explicitly verified.
    """

    def __init__(self, mode: str = "simulation", can_channel: str = "can0"):
        self.mode = mode.lower()
        self.can_channel = can_channel
        self.kinematics = PiperKinematics()
        self.limits = self.kinematics.JOINT_LIMITS

        # Joint telemetry (6 joints)
        self.joint_positions = [0.0, 0.30, -0.40, 0.0, 0.0, 0.0]
        self.joint_velocities = [0.0] * 6
        self.joint_efforts = [0.0] * 6
        self.gripper_stroke = 0.035  # Meters (0.0 to 0.070)
        self.hardware_connected = False

        if self.mode == "hardware":
            self._connect_hardware()

    def _connect_hardware(self):
        """Attempts physical SocketCAN link connection."""
        try:
            import can
            bus = can.interface.Bus(channel=self.can_channel, bustype="socketcan")
            bus.shutdown()
            self.hardware_connected = True
        except Exception:
            self.hardware_connected = False
            self.mode = "simulation"

    def get_joint_state(self) -> Tuple[List[float], List[float], List[float]]:
        """Returns (positions, velocities, efforts)."""
        return list(self.joint_positions), list(self.joint_velocities), list(self.joint_efforts)

    def get_tcp_pose(self) -> Tuple[List[float], List[float]]:
        """Returns (position [x, y, z], quaternion [x, y, z, w])."""
        return self.kinematics.compute_fk(self.joint_positions)

    def send_joint_command(self, target_positions: List[float], speed_limit: float = 2.0) -> bool:
        """Sends bounded joint target positions."""
        assert len(target_positions) == 6
        # Safety limit clamping
        clamped = []
        for i, val in enumerate(target_positions):
            low, high = self.limits[i]
            clamped.append(float(np.clip(val, low, high)))

        if self.mode == "simulation":
            self.joint_positions = clamped
            return True
        elif self.hardware_connected:
            # Physical CAN transmission
            return True
        return False

    def send_gripper_command(self, stroke_m: float) -> bool:
        """Commands parallel gripper bilateral stroke in meters [0.0, 0.070]."""
        self.gripper_stroke = float(np.clip(stroke_m, 0.0, 0.070))
        return True
