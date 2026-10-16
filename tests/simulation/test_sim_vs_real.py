"""
Automated Integration Tests for Sim-vs-Real Trajectory Comparison.
Verifies:
1. Replay of recorded physical telemetry in MuJoCo physics.
2. Quantitative computation of Cartesian and Joint tracking errors.
3. Generation of machine-readable JSON metrics and auditable Markdown reports.
4. Pass/fail boundary assertions on simulation-to-real fidelity.
"""

import os
import json
import pytest
from pathlib import Path

from tools.sim_vs_real import run_sim_vs_real_comparison
from simulation.mujoco_env import HAS_MUJOCO


@pytest.mark.skipif(not HAS_MUJOCO, reason="mujoco not installed")
def test_sim_vs_real_with_live_session(tmp_path):
    """Evaluates sim-vs-real replay against real hardware recording session."""
    h5_path = "data/recordings/live_obs_20261016_170044/session.h5"
    if not os.path.exists(h5_path):
        pytest.skip(f"Live recording {h5_path} not found.")

    out_dir = tmp_path / "sim_vs_real_out"
    metrics = run_sim_vs_real_comparison(
        real_h5_path=h5_path,
        max_steps=20,
        out_dir=str(out_dir),
        render_frames=True,
    )

    assert metrics["fidelity_status"] == "PASS"
    assert metrics["evaluated_steps"] == 20
    assert metrics["cartesian_metrics"]["mae_mm"] < 25.0
    assert metrics["joint_metrics"]["overall_mae_deg"] < 3.0
    assert metrics["gripper_metrics"]["stroke_mae_mm"] < 1.0

    # Verify generated report files
    json_files = list(out_dir.glob("*.json"))
    md_files = list(out_dir.glob("*.md"))
    assert len(json_files) == 1
    assert len(md_files) == 1

    with open(json_files[0], "r", encoding="utf-8") as f:
        data = json.load(f)
        assert "cartesian_metrics" in data
        assert "joint_metrics" in data
