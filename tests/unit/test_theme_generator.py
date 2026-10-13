"""
Unit tests for Thematic Data Generation Engine (JARVIS-PiPER).
Tests generation across core manipulation themes:
- Pick and Place
- Visual Prediction (V-JEPA 2-AC action-conditioned)
- Failure Detection and Recovery
"""

import os
import json
import pytest
from jarvis_piper.tasks.theme_generator import ThematicDatasetGenerator, ManipulationTheme


def test_thematic_generator_pick_and_place(tmp_path):
    out_dir = str(tmp_path / "themes_pick")
    generator = ThematicDatasetGenerator(output_root=out_dir)
    meta = generator.generate_episode(
        theme=ManipulationTheme.PICK_AND_PLACE,
        episode_index=1,
        total_steps=30,
        fps=30.0,
    )

    assert meta["task_theme"] == "pick_and_place"
    assert meta["success_label"] is True
    assert meta["failure_injected"] is False
    assert meta["vjepa_compatible"] is True

    ep_dir = os.path.join(out_dir, meta["episode_id"])
    assert os.path.exists(os.path.join(ep_dir, "metadata.json"))
    assert os.path.exists(os.path.join(ep_dir, "trajectory.json"))
    assert os.path.exists(os.path.join(ep_dir, "stream_journal.jsonl"))

    with open(os.path.join(ep_dir, "trajectory.json"), "r", encoding="utf-8") as f:
        traj = json.load(f)

    assert len(traj["timesteps"]) == 30
    first_step = traj["timesteps"][0]
    assert len(first_step["action"]) == 7  # 6 joints + gripper stroke
    assert "tcp_pose" in first_step


def test_thematic_generator_failure_recovery(tmp_path):
    out_dir = str(tmp_path / "themes_recovery")
    generator = ThematicDatasetGenerator(output_root=out_dir)
    meta = generator.generate_episode(
        theme=ManipulationTheme.FAILURE_RECOVERY,
        episode_index=1,
        total_steps=50,
        fps=30.0,
    )

    assert meta["task_theme"] == "failure_recovery"
    assert meta["failure_injected"] is True
    assert meta["failure_type"] == "grasp_slip"
    assert meta["recovery_executed"] is True

    ep_dir = os.path.join(out_dir, meta["episode_id"])
    with open(os.path.join(ep_dir, "trajectory.json"), "r", encoding="utf-8") as f:
        traj = json.load(f)

    # Verify semantic phases include recovery
    phases = [s.get("semantic_phase") for s in traj["timesteps"]]
    assert "recovery" in phases
    assert "nominal" in phases


def test_thematic_generator_visual_prediction(tmp_path):
    out_dir = str(tmp_path / "themes_vjepa")
    generator = ThematicDatasetGenerator(output_root=out_dir)
    meta = generator.generate_episode(
        theme=ManipulationTheme.VISUAL_PREDICTION,
        episode_index=1,
        total_steps=40,
        fps=30.0,
    )

    assert meta["task_theme"] == "visual_prediction"
    assert meta["vjepa_compatible"] is True
    assert meta["action_conditioned"] is True

    ep_dir = os.path.join(out_dir, meta["episode_id"])
    assert os.path.exists(os.path.join(ep_dir, "metadata.json"))


def test_thematic_generator_curriculum(tmp_path):
    out_dir = str(tmp_path / "curriculum")
    generator = ThematicDatasetGenerator(output_root=out_dir)
    results = generator.generate_starter_curriculum(episodes_per_theme=1)

    assert "pick_and_place" in results
    assert "visual_prediction" in results
    assert "failure_recovery" in results
    assert len(results["pick_and_place"]) == 1
    assert len(results["visual_prediction"]) == 1
    assert len(results["failure_recovery"]) == 1
