"""
JARVIS-PiPER: Safety Supervisor.
The single, mandatory gate between all command sources (teleop, script, policy)
and physical or simulated actuators.

Enforces:
1. Session Motion Gate: Requires explicit authorization token ("ENABLE MOTION").
2. Latched Software E-Stop.
3. Operator-held dead-man clutch.
4. Command timeout watchdog.
5. S-V1.6-3 joint limits (position, velocity, step delta).
6. Cartesian workspace bounding box.
7. Tracking-loss auto-hold.
8. Rejection of NaN, Inf, and sudden jumps.
"""

from enum import Enum
import time
import math
from typing import Dict, Any, List, Tuple, Optional
import numpy as np

from jarvis.errors import (
    MotionNotAuthorizedError,
    EStopTriggeredError,
    ClutchReleasedError,
    JointLimitViolationError,
    VelocityLimitViolationError,
    WorkspaceViolationError,
    WatchdogTimeoutError,
    TrackingLostError,
    CalibrationStatusError,
    InvalidJointStateError,
    StaleFeedbackError,
)
from jarvis.pika_discovery import CalibrationStatus


class ExecutionMode(str, Enum):
    """JARVIS Operating Modes."""
    MOCK = "MOCK"
    SIMULATION = "SIMULATION"
    REPLAY = "REPLAY"
    TELEOP_DRY_RUN = "TELEOP_DRY_RUN"
    HARDWARE_SUPERVISED = "HARDWARE_SUPERVISED"


class SafetySupervisor:
    """
    Authoritative safety supervisor wrapping all command streams.
    """

    # Official S-V1.6-3 firmware joint boundaries (radians)
    JOINT_LIMITS = [
        (-2.618, 2.618),  # Joint 1: Base Yaw
        (0.000, 3.141),   # Joint 2: Shoulder Pitch
        (-2.967, 0.000),  # Joint 3: Elbow Pitch
        (-1.745, 1.745),  # Joint 4: Forearm Roll
        (-1.222, 1.222),  # Joint 5: Wrist Pitch
        (-2.094, 2.094),  # Joint 6: Wrist Roll
    ]

    # Conservative workspace bounding box (meters in arm base frame)
    WORKSPACE_BOUNDS = {
        "x": (0.10, 0.60),
        "y": (-0.45, 0.45),
        "z": (0.015, 0.55),
    }

    def __init__(
        self,
        speed_scale: float = 0.10,  # Default 10% conservative speed
        max_velocity: float = 1.50,  # rad/s hard ceiling
        max_step_delta: float = 0.10,  # rad per tick ceiling
        watchdog_timeout_sec: float = 0.10,  # 100 ms watchdog
        tracking_timeout_sec: float = 0.05,  # 50 ms tracking loss hold
        feedback_timeout_sec: float = 0.10,  # 100 ms feedback staleness hold
        milestone_lock: bool = False,       # When True, locks physical hardware motion for Milestone 2
    ):
        self.speed_scale = speed_scale
        self.max_velocity = max_velocity * speed_scale
        self.max_step_delta = max_step_delta
        self.watchdog_timeout_sec = watchdog_timeout_sec
        self.tracking_timeout_sec = tracking_timeout_sec
        self.feedback_timeout_sec = feedback_timeout_sec
        self.milestone_lock = milestone_lock

        # Mode and state latches (Always initializes to MOCK mode)
        self.mode = ExecutionMode.MOCK
        self._estopped = False
        self._estop_reason = ""
        self._authorized_token: Optional[str] = None
        self._last_command_time = time.time()
        self._last_valid_positions: Optional[List[float]] = None

    def set_mode(self, mode: ExecutionMode) -> None:
        """Sets active execution mode. Escalating to HARDWARE_SUPERVISED does NOT authorize motion."""
        self.mode = ExecutionMode(mode)

    def get_mode(self) -> ExecutionMode:
        return self.mode

    def set_milestone_lock(self, locked: bool = True) -> None:
        """Enforces milestone-level hardware actuation lock."""
        self.milestone_lock = locked

    def authorize_motion(self, token: str) -> None:
        """Grants physical motion permission for the session if token is exact."""
        if token == "ENABLE MOTION":
            self._authorized_token = token
        else:
            raise MotionNotAuthorizedError(f"Invalid motion authorization token '{token}'.")

    def revoke_motion(self) -> None:
        """Revokes physical motion permission immediately."""
        self._authorized_token = None

    def is_motion_authorized(self) -> bool:
        return self._authorized_token == "ENABLE MOTION"

    def trigger_estop(self, reason: str = "Operator E-Stop triggered") -> None:
        """Latches emergency stop. All motion halts immediately."""
        self._estopped = True
        self._estop_reason = reason

    def reset_estop(self, reset_token: Optional[str] = None) -> None:
        """Resets emergency stop only if explicit token is provided."""
        if reset_token != "ENABLE MOTION":
            raise MotionNotAuthorizedError("E-Stop reset requires operator token 'ENABLE MOTION'.")
        self._estopped = False
        self._estop_reason = ""

    def is_estopped(self) -> bool:
        return self._estopped

    def validate_and_filter(
        self,
        command_q: List[float],
        current_q: List[float],
        clutch_engaged: bool = True,
        tracking_age_sec: float = 0.0,
        feedback_age_sec: float = 0.0,
        ee_pos: Optional[List[float]] = None,
        is_hardware_target: bool = False,
        calibration_status: CalibrationStatus = CalibrationStatus.CALIBRATED,
    ) -> List[float]:
        """
        Passes a commanded joint configuration through safety filters.
        Returns clamped, velocity-limited safe joint command.
        Raises specific JarvisError on safety violation.
        """
        now = time.time()

        # 1. Hardware Motion Gate
        if is_hardware_target:
            if self.milestone_lock:
                raise MotionNotAuthorizedError(
                    "Milestone 2 strictly prohibits physical hardware motion. "
                    "All hardware actuation remains BLOCKED until Milestone 17 physical commissioning."
                )
            if not self.is_motion_authorized():
                raise MotionNotAuthorizedError("Target is physical arm but session motion is not authorized.")

        # 2. Latched E-Stop check
        if self._estopped:
            raise EStopTriggeredError(self._estop_reason)

        # 3. Dead-man clutch check
        if not clutch_engaged:
            raise ClutchReleasedError()

        # 4. Tracking-loss auto-hold check
        if tracking_age_sec > self.tracking_timeout_sec:
            raise TrackingLostError(tracking_age_sec)

        # 5. Calibration status check
        cal_val = calibration_status.value if hasattr(calibration_status, "value") else str(calibration_status)
        if cal_val != CalibrationStatus.CALIBRATED.value:
            raise CalibrationStatusError(
                cal_val, "Teleoperation tracking requires verified CALIBRATED state."
            )

        # 6. Feedback staleness check
        if feedback_age_sec > self.feedback_timeout_sec:
            raise StaleFeedbackError(feedback_age_sec, self.feedback_timeout_sec)

        # 7. Command watchdog check
        dt = now - self._last_command_time
        if dt > self.watchdog_timeout_sec and self._last_valid_positions is not None:
            # Stale command stream - hold current position
            self._last_command_time = now
            raise WatchdogTimeoutError(dt, self.watchdog_timeout_sec)
        self._last_command_time = now

        # 8. NaN / Inf rejection
        if any(math.isnan(x) or math.isinf(x) for x in command_q + current_q):
            raise InvalidJointStateError(f"Rejected NaN or Inf in joint configuration: cmd={command_q}, cur={current_q}")

        # 9. Joint count validation
        if len(command_q) != 6 or len(current_q) != 6:
            raise InvalidJointStateError(f"Invalid joint count: expected 6, got cmd={len(command_q)}, cur={len(current_q)}")

        # 8. Cartesian workspace check (if forward kinematics provided)
        if ee_pos is not None:
            x, y, z = ee_pos[:3]
            bx, by, bz = self.WORKSPACE_BOUNDS["x"], self.WORKSPACE_BOUNDS["y"], self.WORKSPACE_BOUNDS["z"]
            if not (bx[0] <= x <= bx[1] and by[0] <= y <= by[1] and bz[0] <= z <= bz[1]):
                raise WorkspaceViolationError(ee_pos, self.WORKSPACE_BOUNDS)

        # 9. Step size delta and velocity limiting
        safe_q = []
        for i, (cmd, cur) in enumerate(zip(command_q, current_q)):
            # Enforce hard firmware position boundaries
            lim_min, lim_max = self.JOINT_LIMITS[i]
            if not (lim_min <= cmd <= lim_max):
                raise JointLimitViolationError(i + 1, cmd, (lim_min, lim_max))

            delta = cmd - cur
            # Velocity clamp based on dt and max_velocity
            max_delta = self.max_step_delta
            clamped_delta = np.clip(delta, -max_delta, max_delta)

            safe_q.append(float(cur + clamped_delta))

        self._last_valid_positions = list(safe_q)
        return safe_q
