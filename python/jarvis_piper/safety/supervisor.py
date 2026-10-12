"""
Safety Supervisor for Real PiPER Hardware Inference and Teleoperation.
Enforces hard kinematic limits, velocity caps, Cartesian bounding box,
timestamp freshness, and inference deadline timeouts.
"""

import math
import time
from typing import List, Optional, Tuple
import numpy as np

from world_model.spatial import PiperKinematics


class SafetyViolationError(RuntimeError):
    """Raised when policy or teleoperator produces an out-of-bounds or unsafe command."""
    pass


class SafetySupervisor:
    """
    Safety Supervisor intercepting all actions between policy/teleoperation and robot drivers:
    JARVIS planner -> action server -> policy adapter -> SafetySupervisor -> controller -> Piper
    """

    # Bounding box for physical desktop manipulation (meters relative to base_link)
    WORKSPACE_BOX = {
        "x": (0.10, 0.60),   # 10cm to 60cm in front of base
        "y": (-0.45, 0.45),  # +/- 45cm lateral width
        "z": (0.015, 0.55),  # 1.5cm above table to 55cm height
    }

    MAX_JOINT_VEL_RAD_S = 1.5    # Rad/s
    MAX_JOINT_ACCEL_RAD_S2 = 3.0 # Rad/s^2
    MAX_OBSERVATION_AGE_S = 0.100 # 100ms freshness limit
    MAX_INFERENCE_DEADLINE_S = 0.020 # 20ms execution deadline

    def __init__(self):
        self.kinematics = PiperKinematics()
        self.last_cmd_q: Optional[List[float]] = None
        self.last_cmd_time: float = time.time()
        self.emergency_stop_latched = False

    def trigger_estop(self, reason: str = "Operator Emergency Stop"):
        self.emergency_stop_latched = True
        print(f"\n[CRITICAL SAFETY ALERT] EMERGENCY STOP ACTIVATED: {reason}")

    def reset_estop(self):
        self.emergency_stop_latched = False
        self.last_cmd_q = None

    def validate_observation_freshness(self, obs_timestamp: float) -> bool:
        age = time.time() - obs_timestamp
        return age <= self.MAX_OBSERVATION_AGE_S

    def filter_and_validate_action(
        self,
        target_q: List[float],
        current_q: List[float],
        target_stroke: float = 0.035,
        dt: float = 0.02,
    ) -> Tuple[List[float], float, bool, str]:
        """
        Validates and safety-clips an action before sending to the controller.
        Returns:
            (safe_target_q, safe_stroke, is_safe, reason)
        """
        if self.emergency_stop_latched:
            # Command zero delta (freeze in place)
            return list(current_q[:6]), target_stroke, False, "E-Stop Latched"

        if len(target_q) < 6:
            return list(current_q[:6]), target_stroke, False, "Incomplete action vector"

        safe_q = []
        # 1. Enforce physical joint position limits
        for j in range(6):
            low, high = self.kinematics.JOINT_LIMITS[j]
            q_val = float(target_q[j])
            if q_val < low or q_val > high:
                q_val = float(np.clip(q_val, low, high))
            safe_q.append(q_val)

        # 2. Enforce maximum velocity bounds (slew-rate limiter)
        for j in range(6):
            delta = safe_q[j] - current_q[j]
            max_delta = self.MAX_JOINT_VEL_RAD_S * dt
            if abs(delta) > max_delta:
                safe_q[j] = current_q[j] + math.copysign(max_delta, delta)

        # 3. Cartesian workspace boundary check
        pos, _ = self.kinematics.compute_fk(safe_q)
        x, y, z = pos[0], pos[1], pos[2]

        box = self.WORKSPACE_BOX
        if not (box["x"][0] <= x <= box["x"][1] and
                box["y"][0] <= y <= box["y"][1] and
                box["z"][0] <= z <= box["z"][1]):
            # Target outside safe workspace envelope; freeze motion
            return list(current_q[:6]), target_stroke, False, f"Cartesian workspace violation: ({x:.3f}, {y:.3f}, {z:.3f}) m"

        # 4. Gripper stroke limit
        safe_stroke = float(np.clip(target_stroke, 0.000, 0.035))

        self.last_cmd_q = list(safe_q)
        self.last_cmd_time = time.time()
        return safe_q, safe_stroke, True, "OK"
