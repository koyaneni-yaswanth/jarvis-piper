"""
Motion Planning Module for AgileX PiPER 6-DOF Manipulator.
Provides:
- Minimum-jerk joint and Cartesian trajectory generation.
- SE(3) linear interpolation between poses.
- Reachability verification via PiperKinematics DLS IK solver.
"""

from typing import List, Tuple, Optional
import os
import sys
_py_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "python"))
if _py_dir not in sys.path:
    sys.path.insert(0, _py_dir)

import numpy as np
from world_model.spatial import PiperKinematics


class MotionPlanner:
    """
    Trajectory and Path Planning for Piper 6-DOF Arm.
    """

    def __init__(self):
        self.kinematics = PiperKinematics()

    def generate_minimum_jerk_joint_trajectory(
        self,
        q_start: List[float],
        q_goal: List[float],
        duration_sec: float = 2.0,
        fps: float = 50.0,
    ) -> List[List[float]]:
        """
        Computes 5th-order polynomial minimum-jerk joint trajectory:
        s(t) = 10*(t/T)^3 - 15*(t/T)^4 + 6*(t/T)^5
        """
        total_steps = max(2, int(duration_sec * fps))
        q0 = np.array(q_start, dtype=np.float64)
        q1 = np.array(q_goal, dtype=np.float64)
        trajectory = []

        for step in range(total_steps):
            tau = step / float(total_steps - 1)
            s = 10.0 * (tau**3) - 15.0 * (tau**4) + 6.0 * (tau**5)
            q_t = q0 + s * (q1 - q0)
            trajectory.append(q_t.tolist())

        return trajectory

    def plan_cartesian_linear_motion(
        self,
        p_start: List[float],
        p_goal: List[float],
        q_seed: List[float],
        steps: int = 20,
    ) -> Tuple[List[List[float]], bool]:
        """
        Interpolates Cartesian straight-line waypoint path and solves IK at each point.
        """
        p0 = np.array(p_start, dtype=np.float64)
        p1 = np.array(p_goal, dtype=np.float64)
        joint_trajectory = []
        current_q = list(q_seed)

        for i in range(steps):
            alpha = i / float(steps - 1)
            p_interp = p0 + alpha * (p1 - p0)
            q_sol, success = self.kinematics.compute_ik(p_interp.tolist(), q_init=current_q)
            if not success:
                return joint_trajectory, False
            joint_trajectory.append(q_sol)
            current_q = q_sol

        return joint_trajectory, True
