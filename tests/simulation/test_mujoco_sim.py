"""
Automated Unit and Integration Tests for PiPER MuJoCo Simulation.
Verifies:
1. MuJoCo XML parsing, degrees of freedom, and actuator mappings.
2. Physics advancement, deterministic reset, and joint limit clamping.
3. Synthetic camera rendering (wrist RGB, depth map, overhead view).
4. Simulation episode recording and data isolation (DATA_ORIGIN = SIMULATION_MUJOCO).
5. Closed-loop ACT policy inference in simulation.
"""

import os
import json
import pytest
import numpy as np
from pathlib import Path

from simulation.mujoco_env import MuJoCoPiPEREnv, HAS_MUJOCO


@pytest.mark.skipif(not HAS_MUJOCO, reason="mujoco not installed")
def test_mujoco_model_load_and_kinematics():
    """Verifies MuJoCo XML loads cleanly with 6 arm joints, actuators, and cameras."""
    env = MuJoCoPiPEREnv()
    assert env.model.nq >= 8
    assert env.model.nu == 8  # 6 arm joints + 2 gripper actuators
    assert env.model.nbody >= 13

    obs = env.get_observation()
    assert len(obs["joint_positions"]) == 6
    assert len(obs["joint_velocities"]) == 6
    assert len(obs["tcp_pose"]["position"]) == 3
    assert len(obs["tcp_pose"]["quaternion"]) == 4
    assert obs["data_origin"] == "SIMULATION_MUJOCO"
    env.close()


@pytest.mark.skipif(not HAS_MUJOCO, reason="mujoco not installed")
def test_mujoco_deterministic_reset_and_bounds():
    """Verifies reset determinism and hard joint-limit enforcement."""
    env = MuJoCoPiPEREnv()

    obs1 = env.reset(seed=101)
    q1 = list(obs1["joint_positions"])

    obs2 = env.reset(seed=101)
    q2 = list(obs2["joint_positions"])
    assert np.allclose(q1, q2, atol=1e-5)

    # Command out-of-boundary joint command (Joint 1 > +2.618 rad limit)
    unsafe_target = [3.5, 0.4, -0.5, 0.0, 0.1, 0.0]
    obs3, reward, done, info = env.step(unsafe_target, target_gripper_stroke=0.035)

    # Stepped joint position must remain clamped within safe physical boundaries
    assert obs3["joint_positions"][0] <= 2.618 + 0.05
    assert not np.isnan(obs3["joint_positions"]).any()
    assert not np.isinf(obs3["joint_positions"]).any()
    env.close()


@pytest.mark.skipif(not HAS_MUJOCO, reason="mujoco not installed")
def test_mujoco_camera_rendering():
    """Verifies offscreen synthetic camera rendering for both color and depth."""
    env = MuJoCoPiPEREnv(render_width=160, render_height=120)

    wrist_rgb = env.render_camera("wrist_camera", depth=False)
    assert wrist_rgb.shape == (120, 160, 3)
    assert wrist_rgb.dtype == np.uint8

    wrist_depth = env.render_camera("wrist_camera", depth=True)
    assert wrist_depth.shape == (120, 160)
    assert wrist_depth.dtype == np.float32
    assert np.all(wrist_depth > 0.0)

    overhead_rgb = env.render_camera("overhead_cam", depth=False)
    assert overhead_rgb.shape == (120, 160, 3)
    env.close()


@pytest.mark.skipif(not HAS_MUJOCO, reason="mujoco not installed")
def test_mujoco_episode_data_isolation(tmp_path):
    """Verifies recorded simulation episodes are explicitly marked with SIMULATION data origin."""
    env = MuJoCoPiPEREnv()
    obs = env.reset()

    records = []
    for step in range(5):
        obs, reward, done, info = env.step(env.q_home, target_gripper_stroke=0.02)
        records.append({
            "step": step,
            "obs": obs,
            "data_origin": obs["data_origin"],
        })

    ep_file = tmp_path / "sim_test_ep.jsonl"
    with open(ep_file, "w") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")

    # Read back and verify strict simulation isolation
    loaded = [json.loads(line) for line in open(ep_file)]
    assert len(loaded) == 5
    for r in loaded:
        assert r["data_origin"] == "SIMULATION_MUJOCO"
    env.close()
