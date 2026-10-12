"""
Unit tests for JARVIS Agent Orchestrator and Autonomous Pick-and-Place.
"""

import pytest
from jarvis_piper.agent.orchestrator import JarvisOrchestrator


def test_jarvis_instruction_parsing():
    agent = JarvisOrchestrator(mode="simulation")

    p1 = agent.parse_instruction("Pick up the red cube and place in blue tray")
    assert p1["intent"] == "pick_and_place"
    assert "red_cube" in p1["args"]["target_object"]
    assert "blue_tray" in p1["args"]["destination"]

    p2 = agent.parse_instruction("Emergency stop!")
    assert p2["intent"] == "emergency_stop"

    p3 = agent.parse_instruction("What are you doing?")
    assert p3["intent"] == "query_status"


def test_jarvis_pick_and_place_execution():
    agent = JarvisOrchestrator(mode="simulation")
    res = agent.execute_command("Pick up the red cube and place in blue tray")

    assert res["status"] == "SUCCESS"
    details = res["details"]
    assert details["grasp_verified"] is True
    assert details["lift_verified"] is True
    assert details["release_verified"] is True
    assert len(agent.episodic_history) == 1
