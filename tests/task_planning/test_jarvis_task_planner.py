"""
Unit tests for JARVIS Natural Language Task Planner (Phase 6).
Verifies:
1. Valid text command parsing ("Pick up the red cube and place in tray").
2. Verification query parsing ("Check whether the object was successfully placed").
3. Rejection of ambiguous, unsupported, or unsafe commands.
"""

import pytest
from task_planning.jarvis_task_planner import JarvisTaskPlanner
from simulation.environment import JarvisSimEnvironment, SimulationConfig


def test_planner_parsing_nominal():
    planner = JarvisTaskPlanner()

    res = planner.parse_instruction("Pick up the red cube and place it in the tray")
    assert res["valid"] is True
    assert res["intent"] == "pick_and_place"
    assert res["target_object"] == "red_cube"
    assert res["destination"] == "tray"


def test_planner_parsing_verify_status():
    planner = JarvisTaskPlanner()

    res = planner.parse_instruction("Check whether the object was successfully placed")
    assert res["valid"] is True
    assert res["intent"] == "verify_state"


def test_planner_rejection_ambiguous():
    planner = JarvisTaskPlanner()

    res = planner.parse_instruction("Throw the dangerous hammer out the window")
    assert res["valid"] is False
    assert "Unsupported" in res["reason"] or "Could not parse" in res["reason"]


def test_planner_execution():
    cfg = SimulationConfig(seed=42, randomize_domain=False)
    env = JarvisSimEnvironment(config=cfg)
    planner = JarvisTaskPlanner(env=env)

    # Execute valid instruction
    res = planner.execute_command("Pick up the red cube and place in the tray", episode_seed=42)
    assert res["status"] == "SUCCESS"
    assert res["metrics"]["placement_success"] is True

    # Execute verification query
    query_res = planner.execute_command("Check whether the object was successfully placed")
    assert query_res["status"] == "SUCCESS"
    assert query_res["object_placed"] is True
