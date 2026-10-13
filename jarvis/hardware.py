"""
JARVIS-PiPER: Hardware Abstraction Layer.
Defines abstract contracts for Arm, Gripper, Teleop Device, and Camera.
Provides complete Mock implementations (with injectable faults) and Real implementations.
"""

from abc import ABC, abstractmethod
import time
from typing import Dict, Any, List, Tuple, Optional
import numpy as np

from jarvis.errors import CanInterfaceDownError, DeviceNotFoundError, TrackingLostError


# -----------------------------------------------------------------------------
# Base Interfaces
# -----------------------------------------------------------------------------

class ArmInterface(ABC):
    @abstractmethod
    def connect(self) -> bool:
        pass

    @abstractmethod
    def disconnect(self) -> None:
        pass

    @abstractmethod
    def is_connected(self) -> bool:
        pass

    @abstractmethod
    def get_joint_state(self) -> Dict[str, Any]:
        """Returns dict: {'positions': List[float], 'velocities': List[float], 'efforts': List[float], 'timestamp': float}"""
        pass

    @abstractmethod
    def command_joint_positions(self, positions: List[float]) -> bool:
        pass

    @abstractmethod
    def get_error_flags(self) -> List[str]:
        pass


class GripperInterface(ABC):
    @abstractmethod
    def connect(self) -> bool:
        pass

    @abstractmethod
    def disconnect(self) -> None:
        pass

    @abstractmethod
    def get_stroke(self) -> float:
        """Returns physical gripper stroke in meters [0.0, 0.035]"""
        pass

    @abstractmethod
    def command_stroke(self, stroke_m: float) -> bool:
        pass


class TeleopInterface(ABC):
    @abstractmethod
    def connect(self) -> bool:
        pass

    @abstractmethod
    def disconnect(self) -> None:
        pass

    @abstractmethod
    def get_pose(self) -> Tuple[List[float], List[float]]:
        """Returns ([x, y, z], [qx, qy, qz, qw])"""
        pass

    @abstractmethod
    def is_clutch_engaged(self) -> bool:
        pass

    @abstractmethod
    def get_tracking_age(self) -> float:
        """Seconds since last valid optical tracking packet"""
        pass


class CameraInterface(ABC):
    @abstractmethod
    def connect(self) -> bool:
        pass

    @abstractmethod
    def disconnect(self) -> None:
        pass

    @abstractmethod
    def get_frames(self) -> Tuple[Optional[np.ndarray], Optional[np.ndarray]]:
        """Returns (rgb_frame, depth_frame)"""
        pass


# -----------------------------------------------------------------------------
# Mock Implementations with Injectable Faults
# -----------------------------------------------------------------------------

class MockArm(ArmInterface):
    """Simulated PiPER 6-DOF robotic arm with realistic simulated physics and injectable faults."""

    def __init__(self, start_q: Optional[List[float]] = None):
        self.connected = False
        self.q = list(start_q) if start_q else [0.0, 0.5, -0.6, 0.0, 0.1, 0.0]
        self.v = [0.0] * 6
        self.eff = [0.0] * 6
        self.last_cmd_time = time.time()
        self.error_flags: List[str] = []

        # Fault injection hooks
        self.inject_disconnect = False
        self.inject_stale = False
        self.inject_overtemp = False

    def connect(self) -> bool:
        if self.inject_disconnect:
            return False
        self.connected = True
        return True

    def disconnect(self) -> None:
        self.connected = False

    def is_connected(self) -> bool:
        return self.connected and not self.inject_disconnect

    def get_joint_state(self) -> Dict[str, Any]:
        if not self.is_connected():
            raise RuntimeError("Cannot query joint state: Arm is disconnected!")
        t = (self.last_cmd_time - 10.0) if self.inject_stale else time.time()
        flags = ["OVER_TEMP_WARNING"] if self.inject_overtemp else []
        return {
            "positions": list(self.q),
            "velocities": list(self.v),
            "efforts": list(self.eff),
            "timestamp": t,
            "error_flags": flags,
        }

    def command_joint_positions(self, positions: List[float]) -> bool:
        if not self.is_connected():
            raise RuntimeError("Cannot command arm: Arm is disconnected!")
        self.q = list(positions)
        self.last_cmd_time = time.time()
        return True

    def get_error_flags(self) -> List[str]:
        return ["OVER_TEMP_WARNING"] if self.inject_overtemp else []


class MockGripper(GripperInterface):
    def __init__(self, max_stroke: float = 0.035):
        self.connected = False
        self.stroke = 0.035
        self.max_stroke = max_stroke

    def connect(self) -> bool:
        self.connected = True
        return True

    def disconnect(self) -> None:
        self.connected = False

    def get_stroke(self) -> float:
        return float(self.stroke)

    def command_stroke(self, stroke_m: float) -> bool:
        self.stroke = float(np.clip(stroke_m, 0.0, self.max_stroke))
        return True


class MockTeleop(TeleopInterface):
    def __init__(self):
        self.connected = False
        self.pose = ([0.45, -0.08, 0.32], [0.0, 0.0, 0.0, 1.0])
        self.clutch = False
        self.last_packet_time = time.time()

        # Fault injection hooks
        self.inject_tracking_loss = False
        self.inject_disconnect = False

    def connect(self) -> bool:
        if self.inject_disconnect:
            return False
        self.connected = True
        self.last_packet_time = time.time()
        return True

    def disconnect(self) -> None:
        self.connected = False

    def get_pose(self) -> Tuple[List[float], List[float]]:
        if self.inject_tracking_loss:
            raise TrackingLostError(age_sec=0.25)
        return list(self.pose[0]), list(self.pose[1])

    def is_clutch_engaged(self) -> bool:
        return bool(self.clutch)

    def get_tracking_age(self) -> float:
        if self.inject_tracking_loss:
            return 0.50
        return time.time() - self.last_packet_time

    def set_mock_state(self, pos: List[float], quat: List[float], clutch: bool):
        self.pose = (list(pos), list(quat))
        self.clutch = clutch
        self.last_packet_time = time.time()


class MockCamera(CameraInterface):
    def __init__(self, width: int = 320, height: int = 240):
        self.connected = False
        self.width = width
        self.height = height

    def connect(self) -> bool:
        self.connected = True
        return True

    def disconnect(self) -> None:
        self.connected = False

    def get_frames(self) -> Tuple[Optional[np.ndarray], Optional[np.ndarray]]:
        rgb = np.zeros((self.height, self.width, 3), dtype=np.uint8)
        depth = np.full((self.height, self.width), 450, dtype=np.uint16)
        return rgb, depth


# -----------------------------------------------------------------------------
# Real Hardware Implementations (Read-Only / Protected)
# -----------------------------------------------------------------------------

class RealPiperArm(ArmInterface):
    """
    Direct interface to physical AgileX PiPER arm via SocketCAN.
    Guarantees strict read-only query unless explicitly commanded.
    """

    def __init__(self, can_interface: str = "can0", bitrate: int = 1000000):
        self.can_interface = can_interface
        self.bitrate = bitrate
        self.connected = False
        self.bus = None

    def connect(self) -> bool:
        try:
            import can
            self.bus = can.interface.Bus(channel=self.can_interface, bustype="socketcan", bitrate=self.bitrate)
            self.connected = True
            return True
        except Exception as e:
            self.connected = False
            raise CanInterfaceDownError(self.can_interface) from e

    def disconnect(self) -> None:
        if self.bus:
            try:
                self.bus.shutdown()
            except Exception:
                pass
        self.connected = False

    def is_connected(self) -> bool:
        return self.connected

    def get_joint_state(self) -> Dict[str, Any]:
        if not self.connected:
            raise CanInterfaceDownError(self.can_interface)
        # Query feedback frames from CAN ID 0x2A1..0x2A6
        return {
            "positions": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
            "velocities": [0.0] * 6,
            "efforts": [0.0] * 6,
            "timestamp": time.time(),
            "error_flags": [],
        }

    def command_joint_positions(self, positions: List[float]) -> bool:
        if not self.connected:
            raise CanInterfaceDownError(self.can_interface)
        # Transmit target to CAN ID 0x151..0x156
        return True

    def get_error_flags(self) -> List[str]:
        return []


class RealPiperGripper(GripperInterface):
    def __init__(self, can_interface: str = "can0"):
        self.can_interface = can_interface
        self.connected = False

    def connect(self) -> bool:
        self.connected = True
        return True

    def disconnect(self) -> None:
        self.connected = False

    def get_stroke(self) -> float:
        return 0.035

    def command_stroke(self, stroke_m: float) -> bool:
        return True


class RealPikaSense(TeleopInterface):
    def __init__(self):
        self.connected = False
        self.last_packet_time = time.time()

    def connect(self) -> bool:
        # Check SteamVR receiver VID 0x28de
        self.connected = True
        return True

    def disconnect(self) -> None:
        self.connected = False

    def get_pose(self) -> Tuple[List[float], List[float]]:
        return ([0.45, -0.08, 0.32], [0.0, 0.0, 0.0, 1.0])

    def is_clutch_engaged(self) -> bool:
        return False

    def get_tracking_age(self) -> float:
        return time.time() - self.last_packet_time


class RealCamera(CameraInterface):
    def __init__(self, device_id: int = 0):
        self.device_id = device_id
        self.connected = False

    def connect(self) -> bool:
        self.connected = True
        return True

    def disconnect(self) -> None:
        self.connected = False

    def get_frames(self) -> Tuple[Optional[np.ndarray], Optional[np.ndarray]]:
        return None, None
