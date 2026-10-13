"""
Baseline Policy: Deterministic Minimum-Jerk Scripted Controller.
Provides gold-standard baseline for task success rate, grasp rate, and repeatability.
"""

from typing import Dict, Any, List, Optional
import numpy as np
import os
import sys
_py_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "python"))
if _py_dir not in sys.path:
    sys.path.insert(0, _py_dir)

from motion_planning.planner import MotionPlanner
from world_model.spatial import PiperKinematics


class ScriptedBaselinePolicy:
    """
    Deterministic motion-planned baseline policy for vision-guided pick-and-place.
    """

    def __init__(self):
        self.planner = MotionPlanner()
        self.kinematics = PiperKinematics()

    def plan_episode_actions(
        self,
        q_current: List[float],
        obj_pos: List[float],
        tray_pos: List[float],
    ) -> List[List[float]]:
        """
        Plans a complete sequence of 7-D actions [q1..q6, gripper_stroke]
        from pick approach to place release.
        """
        obj_p = np.array(obj_pos)
        tray_p = np.array(tray_pos)

        # Pre-grasp waypoint
        p_pre_grasp = obj_p + np.array([0.0, 0.0, 0.06])
        q_pre, _ = self.kinematics.compute_ik(p_pre_grasp.tolist(), q_init=q_current)
        q_grasp, _ = self.kinematics.compute_ik(obj_p.tolist(), q_init=q_pre)

        # Pre-place waypoint
        p_pre_place = tray_p + np.array([0.0, 0.0, 0.06])
        q_pre_place, _ = self.kinematics.compute_ik(p_pre_place.tolist(), q_init=q_grasp)

        actions = []

        # 1. Approach (open gripper = 0.035)
        for q in self.planner.generate_minimum_jerk_joint_trajectory(q_current, q_pre, duration_sec=0.4):
            actions.append(list(q) + [0.035])

        # 2. Descend
        for q in self.planner.generate_minimum_jerk_joint_trajectory(q_pre, q_grasp, duration_sec=0.3):
            actions.append(list(q) + [0.035])

        # 3. Grasp closure (25 steps)
        for _ in range(25):
            actions.append(list(q_grasp) + [0.010])

        # 4. Lift
        for q in self.planner.generate_minimum_jerk_joint_trajectory(q_grasp, q_pre, duration_sec=0.3):
            actions.append(list(q) + [0.010])

        # 5. Transfer
        for q in self.planner.generate_minimum_jerk_joint_trajectory(q_pre, q_pre_place, duration_sec=0.5):
            actions.append(list(q) + [0.010])

        # 6. Release (25 steps)
        for _ in range(25):
            actions.append(list(q_pre_place) + [0.035])

        return actions
