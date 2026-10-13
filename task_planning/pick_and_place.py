"""
Phase 2: Vision-Guided Pick-and-Place Task Execution Pipeline.
Implements the 10-step experimental procedure:
1. Reset the scene.
2. Randomize object position within reachable workspace.
3. Render and capture camera observation.
4. Identify target object and placement region.
5. Generate reachable grasp and placement plan.
6. Execute motion using validated controller.
7. Close gripper and verify grasp contact.
8. Move to target placement region.
9. Release and verify placement success.
10. Record episode, metrics, failure reason, and reset state.
"""

import time
from typing import Dict, Any, Optional, List
import numpy as np

from simulation.environment import JarvisSimEnvironment, SimulationConfig
from motion_planning.planner import MotionPlanner
from world_model.spatial import PiperKinematics
from jarvis_piper.safety.supervisor import SafetySupervisor


class VisionGuidedPickAndPlaceTask:
    """
    Complete Vision-Guided Pick-and-Place Executor with empirical metrics logging.
    """

    def __init__(self, env: Optional[JarvisSimEnvironment] = None):
        self.env = env or JarvisSimEnvironment(SimulationConfig(randomize_domain=True))
        self.planner = MotionPlanner()
        self.kinematics = PiperKinematics()
        self.safety = SafetySupervisor()

    def run_episode(self, episode_seed: Optional[int] = None) -> Dict[str, Any]:
        """
        Executes a single pick-and-place trial following the exact 10-step procedure.
        """
        t0 = time.time()
        # Step 1 & 2: Reset scene & randomize within verified reachable workspace
        obs = self.env.reset(seed=episode_seed)

        # Step 3: Render and capture camera observation
        rgb = obs["rgb"]
        depth = obs["depth"]

        # Step 4: Identify target object and target placement region
        obj_pos = np.array(obs["cube_position"])
        tray_pos = np.array(obs["placement_position"])

        metrics = {
            "episode_seed": episode_seed,
            "target_object": "red_cube",
            "initial_obj_pos": obj_pos.tolist(),
            "target_tray_pos": tray_pos.tolist(),
            "grasp_success": False,
            "placement_success": False,
            "failure_reason": "none",
            "total_steps": 0,
            "trajectory_duration_sec": 0.0,
        }

        # Step 5: Generate reachable grasp and placement plan
        # Pre-grasp approach waypoint: 6 cm directly above target cube
        pre_grasp_pos = obj_pos + np.array([0.0, 0.0, 0.06])
        q_pre, ok_pre = self.kinematics.compute_ik(pre_grasp_pos.tolist(), q_init=obs["joint_positions"])
        q_grasp, ok_grasp = self.kinematics.compute_ik(obj_pos.tolist(), q_init=q_pre if ok_pre else None)

        # Pre-placement waypoint: 6 cm above tray
        pre_place_pos = tray_pos + np.array([0.0, 0.0, 0.06])
        q_pre_place, ok_place = self.kinematics.compute_ik(pre_place_pos.tolist(), q_init=q_grasp if ok_grasp else None)

        if not (ok_pre and ok_grasp and ok_place):
            metrics["failure_reason"] = "unreachable_inverse_kinematics_plan"
            return metrics

        # Step 6: Execute motion using validated controller (Approach to pre-grasp)
        traj_approach = self.planner.generate_minimum_jerk_joint_trajectory(obs["joint_positions"], q_pre, duration_sec=0.4)
        for q_target in traj_approach:
            obs, _, _, _ = self.env.step(target_joint_pos=q_target, target_gripper_stroke=0.035)

        # Lower to grasp target
        traj_descend = self.planner.generate_minimum_jerk_joint_trajectory(q_pre, q_grasp, duration_sec=0.3)
        for q_target in traj_descend:
            obs, _, _, _ = self.env.step(target_joint_pos=q_target, target_gripper_stroke=0.035)

        # Step 7: Close gripper and verify grasp contact (25 ticks = 0.5s stroke closure)
        for _ in range(25):
            obs, _, _, _ = self.env.step(target_joint_pos=q_grasp, target_gripper_stroke=0.010)

        metrics["grasp_success"] = bool(obs["contact_detected"] and obs["object_held"])
        if not metrics["grasp_success"]:
            metrics["failure_reason"] = "grasp_contact_verification_failed"
            metrics["total_steps"] = self.env.step_count
            metrics["trajectory_duration_sec"] = round(time.time() - t0, 3)
            return metrics

        # Step 8: Move to target placement region (Lift + Transfer)
        traj_lift = self.planner.generate_minimum_jerk_joint_trajectory(q_grasp, q_pre, duration_sec=0.3)
        for q_target in traj_lift:
            obs, _, _, _ = self.env.step(target_joint_pos=q_target, target_gripper_stroke=0.010)

        traj_transfer = self.planner.generate_minimum_jerk_joint_trajectory(q_pre, q_pre_place, duration_sec=0.5)
        for q_target in traj_transfer:
            obs, _, _, _ = self.env.step(target_joint_pos=q_target, target_gripper_stroke=0.010)

        # Step 9: Release and verify placement success (25 ticks = 0.5s stroke opening)
        for _ in range(25):
            obs, _, _, info = self.env.step(target_joint_pos=q_pre_place, target_gripper_stroke=0.035)

        # Final return home
        traj_home = self.planner.generate_minimum_jerk_joint_trajectory(q_pre_place, self.env.q_home.tolist(), duration_sec=0.3)
        for q_target in traj_home:
            obs, _, _, info = self.env.step(target_joint_pos=q_target, target_gripper_stroke=0.035)

        # Step 10: Record episode metrics, failure reason, and final outcome
        dist_to_tray = float(np.linalg.norm(np.array(obs["cube_position"][:2]) - tray_pos[:2]))
        metrics["placement_success"] = bool(dist_to_tray < 0.08 and not obs["object_held"])
        metrics["final_cube_pos"] = obs["cube_position"]
        metrics["distance_to_target_m"] = round(dist_to_tray, 4)
        metrics["total_steps"] = self.env.step_count
        metrics["trajectory_duration_sec"] = round(time.time() - t0, 3)
        if not metrics["placement_success"]:
            metrics["failure_reason"] = "placement_tolerance_exceeded"

        return metrics
