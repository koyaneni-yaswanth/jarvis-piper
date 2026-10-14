"""
DEPRECATED — DO NOT USE IN NEW CODE.

This module (`safety/safety_supervisor.py`) is a legacy artifact with an incompatible
method signature. The canonical implementation is:

    from jarvis_piper.safety.supervisor import SafetySupervisor

Key API difference:
  LEGACY:    validate_joint_command(target, current, dt) -> (is_safe, sanitized, reason)
  CANONICAL: filter_and_validate_action(target_q, current_q, dt) -> (safe_q, stroke, is_safe, reason)

This file is retained for reference only. All production code, ROS nodes, policies,
and teleoperation controllers MUST use the canonical implementation.
This file will be removed in the next cleanup commit once all references are migrated.

Phase 7: Independent Safety Architecture for AgileX PiPER 6-DOF.
Enforces multi-layer safety independent of any neural network or task planner:
- Joint position soft-stop limits.
- Cartesian workspace bounding box.
- Joint velocity clamps.
- Latched Emergency Stop (E-Stop).
- Hardware interlock requiring deliberate operator confirmation before physical execution.
- Communication loss timeout monitoring.
"""

from typing import List, Tuple, Dict, Any, Optional
import time
import numpy as np
import os
import sys
_py_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "python"))
if _py_dir not in sys.path:
    sys.path.insert(0, _py_dir)

from world_model.spatial import PiperKinematics


class SafetySupervisor:
    """
    Independent Safety Layer governing all robot control commands.
    """

    # Physical Piper joint limits (radians) with 3-degree safety margin
    JOINT_LIMITS = [
        (-2.55, 2.55),
        (0.05, 3.10),
        (-2.90, -0.05),
        (-1.70, 1.70),
        (-1.18, 1.18),
        (-2.05, 2.05),
    ]

    # Workspace Bounding Box relative to arm base (meters)
    WORKSPACE_X = (0.15, 0.62)
    WORKSPACE_Y = (-0.40, 0.40)
    WORKSPACE_Z = (0.12, 0.60)

    # Maximum joint velocities (rad/s)
    MAX_VELOCITY_RAD_S = 1.5  # Safe commissioning speed

    def __init__(self, mode: str = "simulation"):
        self.mode = mode.lower()
        self.kinematics = PiperKinematics()
        self.estop_latched = False
        self.last_heartbeat = time.time()
        self.heartbeat_timeout_sec = 0.5
        self.hardware_confirmed = False

    def trigger_estop(self, reason: str = "Operator Triggered"):
        """Latches emergency stop. All motion commands are immediately rejected."""
        self.estop_latched = True
        print(f" [E-STOP ENGAGED] {reason}")

    def reset_estop(self, confirmation_token: str) -> bool:
        """Resets E-stop only with intentional confirmation token."""
        if confirmation_token == "CONFIRM_SAFE_RESET":
            self.estop_latched = False
            self.last_heartbeat = time.time()
            return True
        return False

    def authorize_physical_execution(self, operator_key: str) -> bool:
        """Explicit interlock: Requires manual operator authorization before any physical CAN send."""
        if operator_key == "OPERATOR_COMMISSIONING_CONFIRMED":
            self.hardware_confirmed = True
            return True
        return False

    def validate_joint_command(
        self,
        target_positions: List[float],
        current_positions: Optional[List[float]] = None,
        dt: float = 0.02,
    ) -> Tuple[bool, List[float], str]:
        """
        Validates target joint positions against limits, velocity bounds, and E-stop.
        Returns:
            (is_safe, sanitized_command, reason)
        """
        if self.estop_latched:
            return False, list(current_positions or target_positions), "E-STOP LATCHED: Command blocked"

        if len(target_positions) != 6:
            return False, [], "Invalid joint command dimension (expected 6)"

        # Check heartbeat timeout
        if time.time() - self.last_heartbeat > self.heartbeat_timeout_sec:
            self.trigger_estop("Communication heartbeat timeout")
            return False, list(current_positions or target_positions), "Heartbeat lost"

        sanitized = []
        for i, val in enumerate(target_positions):
            low, high = self.JOINT_LIMITS[i]
            if val < low or val > high:
                clamped = float(np.clip(val, low, high))
                sanitized.append(clamped)
            else:
                sanitized.append(float(val))

        # Check velocity bounds if current positions are provided
        if current_positions is not None and len(current_positions) == 6:
            for i in range(6):
                vel = abs(sanitized[i] - current_positions[i]) / max(1e-4, dt)
                if vel > self.MAX_VELOCITY_RAD_S:
                    # Scale back to max allowable velocity
                    delta = np.sign(sanitized[i] - current_positions[i]) * self.MAX_VELOCITY_RAD_S * dt
                    sanitized[i] = current_positions[i] + delta

        # Check Cartesian workspace bounds via Forward Kinematics
        fk_pos, _ = self.kinematics.compute_fk(sanitized)
        x, y, z = fk_pos
        if not (self.WORKSPACE_X[0] <= x <= self.WORKSPACE_X[1] and
                self.WORKSPACE_Y[0] <= y <= self.WORKSPACE_Y[1] and
                self.WORKSPACE_Z[0] <= z <= self.WORKSPACE_Z[1]):
            return False, list(current_positions or sanitized), f"Cartesian workspace violation: {[round(p, 3) for p in fk_pos]}"

        return True, sanitized, "SAFE"

    def record_heartbeat(self):
        """Updates communication heartbeat timestamp."""
        self.last_heartbeat = time.time()
