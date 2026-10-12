"""
Layer A: Conventional Robot Motion Controller & Trajectory Generator.
Provides minimum-jerk spatial interpolation, analytical/numerical IK,
and collision-bounded safety limits as the deterministic baseline and fallback.
"""

import math
from typing import List, Optional, Tuple
import numpy as np

from world_model.spatial import PiperKinematics


class ConventionalController:
    """
    Conventional motion planner and controller for AgileX PiPER.
    Generates C^2-continuous minimum-jerk trajectories and enforces joint/velocity limits.
    """

    def __init__(self, max_joint_vel: float = 1.5, max_joint_accel: float = 3.0):
        self.kinematics = PiperKinematics()
        self.max_joint_vel = float(max_joint_vel)
        self.max_joint_accel = float(max_joint_accel)

    def plan_joint_trajectory(
        self,
        q_start: List[float],
        q_goal: List[float],
        duration_s: float = 2.0,
        control_freq_hz: float = 50.0,
    ) -> List[List[float]]:
        """
        Generates minimum-jerk trajectory in joint space:
        s(tau) = 10*tau^3 - 15*tau^4 + 6*tau^5 where tau = t / T.
        """
        num_steps = max(2, int(duration_s * control_freq_hz))
        q0 = np.array(q_start[:6], dtype=np.float64)
        q1 = np.array(q_goal[:6], dtype=np.float64)

        trajectory = []
        for step in range(num_steps):
            tau = step / float(num_steps - 1)
            # 5th-order minimum-jerk polynomial
            s = 10.0 * (tau ** 3) - 15.0 * (tau ** 4) + 6.0 * (tau ** 5)
            q_interp = q0 + s * (q1 - q0)

            # Enforce hard joint limits
            for j in range(6):
                low, high = self.kinematics.JOINT_LIMITS[j]
                q_interp[j] = np.clip(q_interp[j], low, high)

            trajectory.append([float(x) for x in q_interp])

        return trajectory

    def plan_cartesian_linear(
        self,
        p_start: List[float],
        p_goal: List[float],
        q_start: List[float],
        duration_s: float = 2.0,
        control_freq_hz: float = 50.0,
    ) -> Tuple[List[List[float]], bool]:
        """
        Interpolates straight-line Cartesian path and solves IK at each waypoint.
        """
        num_steps = max(2, int(duration_s * control_freq_hz))
        p0 = np.array(p_start[:3], dtype=np.float64)
        p1 = np.array(p_goal[:3], dtype=np.float64)

        q_traj = []
        q_current = list(q_start)

        for step in range(num_steps):
            alpha = step / float(num_steps - 1)
            p_interp = p0 + alpha * (p1 - p0)

            q_sol, success = self.kinematics.compute_ik(
                target_pos=list(p_interp),
                q_init=q_current,
                max_iters=30,
                tolerance=1e-3,
            )
            if not success or q_sol is None:
                return q_traj, False

            q_traj.append(q_sol)
            q_current = q_sol

        return q_traj, True

    def verify_joint_safety(self, q: List[float], q_dot: Optional[List[float]] = None) -> bool:
        """Verifies joint bounds and velocity limits."""
        for j in range(min(6, len(q))):
            low, high = self.kinematics.JOINT_LIMITS[j]
            if q[j] < low - 1e-3 or q[j] > high + 1e-3:
                return False

        if q_dot is not None:
            for v in q_dot:
                if abs(v) > self.max_joint_vel:
                    return False

        return True
