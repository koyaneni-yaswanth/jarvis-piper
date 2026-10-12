"""
Unit and round-trip tests for UniversalDatasetExporter (LeRobot, ALOHA HDF5, RLDS, Manifest).
"""

import json
import os
import tempfile
import numpy as np
import pytest

from dataset.exporters import UniversalExporter, HAS_H5PY


@pytest.fixture
def sample_raw_dataset(tmp_path):
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()

    for ep_idx in range(3):
        ep_dir = raw_dir / f"ep_{ep_idx:03d}"
        ep_dir.mkdir()

        metadata = {
            "episode_id": f"ep_{ep_idx:03d}",
            "task_instruction": "Pick up red cube and place in tray",
            "is_synthetic": True,
            "source_label": "SYNTHETIC",
            "duration_sec": 3.0,
        }

        timesteps = []
        for t in range(30):
            timesteps.append({
                "step_index": t,
                "timestamp": float(t) * 0.0333,
                "joint_positions": [0.1 * ep_idx, -0.2, 0.3, 0.0, 0.0, 0.0],
                "joint_velocities": [0.0] * 6,
                "joint_efforts": [0.5] * 6,
                "gripper_stroke": 0.035 - (0.001 * t),
                "action": [0.1 * ep_idx, -0.2, 0.3, 0.0, 0.0, 0.0],
            })

        traj_file = ep_dir / "trajectory.json"
        with open(traj_file, "w", encoding="utf-8") as f:
            json.dump({"metadata": metadata, "timesteps": timesteps}, f)

    return str(raw_dir)


def test_exporter_round_trip(sample_raw_dataset, tmp_path):
    export_root = str(tmp_path / "exported")
    exporter = UniversalExporter(raw_dir=sample_raw_dataset, export_root=export_root)

    res = exporter.export_all(target_format="all")
    assert res["total_episodes"] == 3
    assert "lerobot" in res["formats"]
    assert "aloha" in res["formats"]
    assert "rlds" in res["formats"]
    assert res["manifest"] is not None

    # Check manifest exists and has expected fields
    with open(res["manifest"], "r", encoding="utf-8") as f:
        manifest = json.load(f)
    assert manifest["dataset_version"] == "2.1.0"
    assert manifest["total_episodes"] == 3
    assert len(manifest["episodes"]) == 3

    # Verification round-trip
    verif = exporter.verify_exported_datasets()
    assert verif["lerobot"]["valid"] is True
    assert verif["manifest"]["valid"] is True

    if HAS_H5PY:
        assert verif["aloha_hdf5"]["valid"] is True
        assert verif["aloha_hdf5"]["qpos_shape"] == [30, 8]
    else:
        assert verif["aloha_npz"]["valid"] is True
