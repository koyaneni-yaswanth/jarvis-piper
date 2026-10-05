"""
Unit tests for Quality Scorer and Trajectory Auditing.
"""

import json
from pathlib import Path
from dataset.quality import QualityScorer
from evaluation.metrics import compute_trajectory_jerk, compute_sync_jitter
import numpy as np


def test_jerk_calculation():
    # Perfectly constant velocity trajectory has zero jerk
    t = np.linspace(0, 1, 50)
    pos = np.stack([t, 2*t, -t], axis=-1)
    jerk = compute_trajectory_jerk(pos, dt=0.02)
    assert np.isclose(jerk, 0.0, atol=1e-3)


def test_sync_jitter_metrics():
    # Regular 50Hz timestamps (0.02s interval)
    ts = [i * 0.02 for i in range(100)]
    stats = compute_sync_jitter(ts, expected_hz=50.0)
    assert np.isclose(stats["mean_dt_ms"], 20.0, atol=0.1)
    assert stats["drop_ratio"] == 0.0


def test_quality_scorer_audit(tmp_path):
    ep_dir = tmp_path / "ep_test"
    ep_dir.mkdir()

    meta = {
        "episode_id": "ep_test",
        "task_instruction": "Test",
        "total_steps": 20,
        "success_label": True,
    }
    with open(ep_dir / "metadata.json", "w") as f:
        json.dump(meta, f)

    timesteps = []
    for i in range(20):
        timesteps.append({
            "step_index": i,
            "timestamp": i * 0.02,
            "joint_positions": [0.0] * 6,
            "gripper_stroke": 0.02,
        })
    with open(ep_dir / "trajectory.json", "w") as f:
        json.dump({"metadata": meta, "timesteps": timesteps}, f)

    scorer = QualityScorer()
    res = scorer.audit_episode(str(ep_dir))
    assert res["passed"] is True
    assert res["quality_tier"] in ("A", "B")
