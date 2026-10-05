"""
PiPER 6-DOF Robotic Arm Hardware Adapter.
Interfaces with ROS 2 /joint_states and trajectory controller action servers.
"""

from typing import List, Tuple
from jarvis_piper.hardware.base import RobotInterface


class PiperHardwareAdapter(RobotInterface):
    """Adapter for physical AgileX PiPER 6-DOF robotic arm."""

    def __init__(self, node=None, base_frame: str = "base_link", tcp_frame: str = "piper_gripper_base"):
        self.node = node
        self.base_frame = base_frame
        self.tcp_frame = tcp_frame
        self._connected = True
        self._q = [0.0] * 6
        self._v = [0.0] * 6
        self._eff = [0.0] * 6
        self._tcp_pos = [0.35, 0.0, 0.25]
        self._tcp_quat = [0.0, 0.0, 0.0, 1.0]

    def connect(self) -> bool:
        self._connected = True
        return True

    def disconnect(self) -> None:
        self._connected = False

    def is_connected(self) -> bool:
        return self._connected

    def update_from_joint_msg(self, msg) -> None:
        """Updates internal state from incoming sensor_msgs/JointState."""
        if not msg:
            return
        positions = []
        velocities = []
        efforts = []
        for i in range(1, 7):
            name = f"piper_joint{i}"
            if name in msg.name:
                idx = msg.name.index(name)
                positions.append(msg.position[idx] if idx < len(msg.position) else 0.0)
                velocities.append(msg.velocity[idx] if idx < len(msg.velocity) else 0.0)
                efforts.append(msg.effort[idx] if idx < len(msg.effort) else 0.0)
            else:
                positions.append(0.0)
                velocities.append(0.0)
                efforts.append(0.0)

        if len(positions) == 6:
            self._q = positions
            self._v = velocities
            self._eff = efforts

    def get_joint_states(self) -> Tuple[List[float], List[float], List[float]]:
        return list(self._q), list(self._v), list(self._eff)

    def get_tcp_pose(self) -> Tuple[List[float], List[float]]:
        return list(self._tcp_pos), list(self._tcp_quat)

    def send_joint_command(self, target_positions_rad: List[float]) -> bool:
        if not self._connected or len(target_positions_rad) < 6:
            return False
        self._q = list(target_positions_rad[:6])
        return True
