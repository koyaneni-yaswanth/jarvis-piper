"""
Deterministic Smoke Test for JarvisSimEnvironment (Phase 1).
Verifies:
1. Environment instantiation and deterministic reset.
2. Safe joint trajectory tracking and physics advancement.
3. Multimodal sensor observations (RGB, depth, joint positions, velocities, TCP pose).
4. Gripper stroke dynamics and contact verification.
"""

import numpy as np
import pytest
from simulation.environment import JarvisSimEnvironment, SimulationConfig


def test_sim_environment_instantiation_and_reset():
    cfg = SimulationConfig(seed=123, randomize_domain=False)
    env = JarvisSimEnvironment(config=cfg)

    obs = env.reset(seed=123)
    assert "joint_positions" in obs
    assert len(obs["joint_positions"]) == 6
    assert "tcp_pose" in obs
    assert "position" in obs["tcp_pose"]
    assert "orientation" in obs["tcp_pose"]
    assert "rgb" in obs
    assert obs["rgb"].shape == (240, 320, 3)
    assert "depth" in obs
    assert obs["depth"].shape == (240, 320)
    assert obs["step_count"] == 0
    assert obs["object_held"] is False


def test_sim_environment_deterministic_trajectory_stepping():
    cfg = SimulationConfig(seed=42, randomize_domain=False)
    env = JarvisSimEnvironment(config=cfg)
    env.reset(seed=42)

    # Step through a safe multi-step reaching trajectory
    q_target = [0.20, 0.45, -0.60, 0.10, 0.15, 0.05]
    gripper_target = 0.015

    for step in range(25):
        obs, reward, done, info = env.step(target_joint_pos=q_target, target_gripper_stroke=gripper_target)
        assert not np.isnan(obs["joint_positions"]).any()
        assert not np.isinf(obs["joint_positions"]).any()
        assert not np.isnan(obs["joint_velocities"]).any()
        assert 0.0 <= obs["gripper_stroke"] <= 0.070

    # Ensure joints moved closer to target
    final_q = np.array(obs["joint_positions"])
    target_q_arr = np.array(q_target)
    tracking_err = float(np.linalg.norm(target_q_arr - final_q))
    assert tracking_err < 0.15, f"Tracking error {tracking_err} exceeded limit"
    assert obs["step_count"] == 25


def test_sim_environment_grasp_and_contact():
    cfg = SimulationConfig(seed=99, randomize_domain=False)
    env = JarvisSimEnvironment(config=cfg)
    env.reset(seed=99)

    # Move TCP directly to cube position
    cube_pos = env.cube.position
    # Use Piper IK to reach near cube
    q_sol, success = env.kinematics.compute_ik(cube_pos.tolist(), [0.0, 0.0, 0.0, 1.0])
    assert success, "IK solver should reach cube in nominal workspace"

    # Move to cube with open gripper
    for _ in range(25):
        env.step(target_joint_pos=q_sol, target_gripper_stroke=0.035)

    # Close gripper to grasp
    for _ in range(25):
        obs, reward, done, info = env.step(target_joint_pos=q_sol, target_gripper_stroke=0.010)

    # Grasp should register contact
    assert obs["contact_detected"] is True
    assert obs["object_held"] is True
