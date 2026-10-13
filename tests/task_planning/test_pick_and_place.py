"""
Unit test for Phase 2: VisionGuidedPickAndPlaceTask.
Verifies complete 10-step pick-and-place execution:
- Pre-grasp approach
- Grasp contact verification
- Vertical lifting
- Lateral transport
- Release and outcome measurement
"""

import pytest
from task_planning.pick_and_place import VisionGuidedPickAndPlaceTask
from simulation.environment import JarvisSimEnvironment, SimulationConfig


def test_pick_and_place_task_nominal():
    cfg = SimulationConfig(seed=42, randomize_domain=False)
    env = JarvisSimEnvironment(config=cfg)
    task = VisionGuidedPickAndPlaceTask(env=env)

    metrics = task.run_episode(episode_seed=42)

    assert metrics["grasp_success"] is True, "Grasp should succeed in nominal scenario"
    assert metrics["placement_success"] is True, "Placement should succeed in nominal scenario"
    assert metrics["distance_to_target_m"] < 0.08, "Cube should be inside placement tray"
    assert metrics["total_steps"] > 50, "Episode should contain all movement phases"
    assert metrics["failure_reason"] == "none"


def test_pick_and_place_multiple_seeds():
    cfg = SimulationConfig(randomize_domain=True)
    env = JarvisSimEnvironment(config=cfg)
    task = VisionGuidedPickAndPlaceTask(env=env)

    success_count = 0
    trials = 3

    for seed in [101, 102, 103]:
        metrics = task.run_episode(episode_seed=seed)
        if metrics["placement_success"]:
            success_count += 1

    # At least 2/3 should pass in random workspace configurations
    assert success_count >= 2, f"Success rate {success_count}/{trials} too low"
