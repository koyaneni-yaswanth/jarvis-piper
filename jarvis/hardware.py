"""
JARVIS-PiPER: Hardware Abstraction Layer.
Defines abstract contracts for Arm, Gripper, Teleop Device, and Camera.
Provides complete Mock implementations (with injectable faults) and Real implementations.
"""

from abc import ABC, abstractmethod
import time
import math
from typing import Dict, Any, List, Tuple, Optional
import numpy as np

from jarvis.errors import (
    CanInterfaceDownError,
    DeviceNotFoundError,
    TrackingLostError,
    HardwareUnavailableError,
    InvalidJointStateError,
    StaleFeedbackError,
    MotionNotAuthorizedError,
)


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
        """Returns dict: {'positions': List[float], 'velocities': List[float], 'efforts': List[float], 'timestamp': float, 'freshness_sec': float, 'error_flags': List[str]}"""
        pass

    @abstractmethod
    def get_feedback_freshness(self) -> float:
        """Returns elapsed time in seconds since last received telemetry packet."""
        pass

    @abstractmethod
    def get_communication_errors(self) -> List[str]:
        """Returns active communication error strings."""
        pass

    @abstractmethod
    def get_mode(self) -> str:
        """Returns active operating mode (e.g. MOCK, HARDWARE)."""
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
        self.inject_nan = False
        self.inject_wrong_count = False
        self.inject_comm_error = False
        self.inject_overtemp = False

    def connect(self) -> bool:
        if self.inject_disconnect:
            return False
        self.connected = True
        self.last_cmd_time = time.time()
        return True

    def disconnect(self) -> None:
        self.connected = False

    def is_connected(self) -> bool:
        return self.connected and not self.inject_disconnect

    def get_feedback_freshness(self) -> float:
        if not self.is_connected():
            return float("inf")
        if self.inject_stale:
            return 10.0
        return max(0.0, time.time() - self.last_cmd_time)

    def get_communication_errors(self) -> List[str]:
        errors = []
        if self.inject_comm_error:
            errors.append("CAN_RX_FIFO_OVERFLOW")
        if self.inject_disconnect or not self.connected:
            errors.append("DEVICE_DISCONNECTED")
        return errors

    def get_mode(self) -> str:
        return "MOCK"

    def get_joint_state(self) -> Dict[str, Any]:
        if not self.is_connected():
            raise HardwareUnavailableError("MockArm", "Cannot query joint state: Arm is disconnected!")
        t = (self.last_cmd_time - 10.0) if self.inject_stale else time.time()
        flags = list(self.error_flags)
        if self.inject_overtemp:
            flags.append("OVER_TEMP_WARNING")

        if self.inject_nan:
            positions = [float("nan")] * 6
        elif self.inject_wrong_count:
            positions = [0.0] * 5
        else:
            positions = list(self.q)

        return {
            "positions": positions,
            "velocities": list(self.v),
            "efforts": list(self.eff),
            "timestamp": t,
            "freshness_sec": self.get_feedback_freshness(),
            "error_flags": flags,
        }

    def command_joint_positions(self, positions: List[float]) -> bool:
        if not self.is_connected():
            raise HardwareUnavailableError("MockArm", "Cannot command arm: Arm is disconnected!")
        self.q = list(positions)
        self.last_cmd_time = time.time()
        return True

    def get_error_flags(self) -> List[str]:
        flags = list(self.error_flags)
        if self.inject_overtemp:
            flags.append("OVER_TEMP_WARNING")
        return flags


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
        self.last_packet_time = 0.0
        self.last_positions = [0.0] * 6
        self.last_velocities = [0.0] * 6
        self.last_efforts = [0.0] * 6
        self.comm_errors = []

    def connect(self) -> bool:
        try:
            import can
            self.bus = can.interface.Bus(channel=self.can_interface, bustype="socketcan", bitrate=self.bitrate)
            self.connected = True
            return True
        except Exception as e:
            self.connected = False
            self.comm_errors.append(f"CAN connect failed: {e}")
            raise CanInterfaceDownError(self.can_interface) from e

    def disconnect(self) -> None:
        if self.bus:
            try:
                self.bus.shutdown()
            except Exception:
                pass
            self.bus = None
        self.connected = False

    def is_connected(self) -> bool:
        return self.connected and self.bus is not None

    def get_feedback_freshness(self) -> float:
        if not self.is_connected() or self.last_packet_time == 0.0:
            return float("inf")
        return max(0.0, time.time() - self.last_packet_time)

    def get_communication_errors(self) -> List[str]:
        return list(self.comm_errors)

    def get_mode(self) -> str:
        return "HARDWARE" if self.is_connected() else "DISCONNECTED"

    def get_joint_state(self) -> Dict[str, Any]:
        if not self.connected or not self.bus:
            raise CanInterfaceDownError(self.can_interface)

        # Passive non-blocking receive of available frames
        try:
            while True:
                msg = self.bus.recv(timeout=0.005)
                if msg is None:
                    break
                # Joint feedback CAN IDs 0x2A1..0x2A6
                if 0x2A1 <= msg.arbitration_id <= 0x2A6:
                    j_idx = msg.arbitration_id - 0x2A1
                    if len(msg.data) >= 2:
                        raw_deg = int.from_bytes(msg.data[0:2], byteorder="little", signed=True)
                        rad = (raw_deg * 0.001) * (math.pi / 180.0)
                        self.last_positions[j_idx] = float(rad)
                        self.last_packet_time = time.time()
        except Exception as e:
            self.comm_errors.append(f"CAN read error: {e}")

        freshness = self.get_feedback_freshness()
        return {
            "positions": list(self.last_positions),
            "velocities": list(self.last_velocities),
            "efforts": list(self.last_efforts),
            "timestamp": self.last_packet_time,
            "freshness_sec": freshness,
            "error_flags": list(self.comm_errors),
        }

    def command_joint_positions(self, positions: List[float]) -> bool:
        if not self.connected:
            raise CanInterfaceDownError(self.can_interface)
        # Milestone 2 strictly prohibits physical hardware motion
        raise MotionNotAuthorizedError(
            "Milestone 2 strictly prohibits physical hardware motion. "
            "All physical hardware actuation remains BLOCKED until Milestone 17 physical commissioning."
        )

    def get_error_flags(self) -> List[str]:
        return list(self.comm_errors)


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
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path
        self.connected = False
        self.last_packet_time = 0.0
        self.last_pose = ([0.45, -0.08, 0.32], [0.0, 0.0, 0.0, 1.0])
        self.clutch_engaged = False
        self.report = None

    def connect(self) -> bool:
        from jarvis.pika_discovery import PikaDiscovery
        self.report = PikaDiscovery.discover(config_path=self.config_path)
        if not self.report.detected:
            self.connected = False
            raise DeviceNotFoundError("SteamVR Wireless Receiver", "VID 0x28de, PID 0x2101")
        self.connected = True
        self.last_packet_time = time.time()
        return True

    def disconnect(self) -> None:
        self.connected = False

    def is_connected(self) -> bool:
        return self.connected

    def get_pose(self) -> Tuple[List[float], List[float]]:
        if not self.connected:
            raise DeviceNotFoundError("SteamVR Wireless Receiver", "VID 0x28de")
        return list(self.last_pose[0]), list(self.last_pose[1])

    def is_clutch_engaged(self) -> bool:
        return bool(self.clutch_engaged)

    def get_tracking_age(self) -> float:
        if not self.connected or self.last_packet_time == 0.0:
            return float("inf")
        return max(0.0, time.time() - self.last_packet_time)


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
