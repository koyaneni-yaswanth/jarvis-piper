"""
Unit tests for Phase 3: Dataset Recording, Validation, and Replay Pipeline.
"""

import os
import pytest
import numpy as np
from data.recording.recorder import DatasetEpisodeRecorder
from data.validation.validator import DatasetValidator
from data.recording.replay import EpisodeReplayer


def test_recorder_and_validator_roundtrip(tmp_path):
    dataset_dir = str(tmp_path / "test_dataset")
    recorder = DatasetEpisodeRecorder(output_root=dataset_dir)

    ep_id = recorder.start_episode(task_id="smoke_task", instruction="Test recording", seed=7)

    # Record 10 nominal steps
    for step in range(10):
        obs = {
            "joint_positions": [0.1 * step] * 6,
            "joint_velocities": [0.05] * 6,
            "gripper_stroke": 0.035,
            "tcp_pose": {"position": [0.4, 0.0, 0.3], "orientation": [0, 0, 0, 1]},
            "contact_detected": False,
            "object_held": False,
            "rgb": np.zeros((240, 320, 3), dtype=np.uint8),
            "depth": np.zeros((240, 320), dtype=np.uint16),
        }
        action = [0.1 * step] * 6 + [0.035]
        recorder.record_step(step_index=step, obs=obs, action=action)

    meta = recorder.end_episode(success=True)
    assert meta["total_steps"] == 10
    assert meta["success_label"] is True

    # Audit using validator
    ep_dir = os.path.join(dataset_dir, ep_id)
    validator = DatasetValidator(dataset_path=dataset_dir)
    report = validator.audit_episode(ep_dir)

    assert report["valid"] is True
    assert report["is_monotonic"] is True
    assert report["has_nan"] is False
    assert report["total_steps"] == 10

    # Verify replay
    replayer = EpisodeReplayer(episode_dir=ep_dir)
    steps = list(replayer.stream_steps(playback_speed=0))  # zero delay
    assert len(steps) == 10
    assert steps[0]["step_index"] == 0
    assert steps[-1]["step_index"] == 9
