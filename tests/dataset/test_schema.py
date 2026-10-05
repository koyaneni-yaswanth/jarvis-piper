"""
Unit tests for dataset schema verification.
"""

from dataset.schema import (
    EpisodeMetadata,
    Timestep,
    TCPPose,
    validate_episode_directory,
)


def test_metadata_dataclass():
    meta = EpisodeMetadata(
        episode_id="ep_test_001",
        task_instruction="Pick cube",
        task_category="pick_and_place",
        operator_id="test_op",
        duration_sec=3.5,
        total_steps=100,
        target_fps=30.0,
    )
    d = meta.to_dict()
    assert d["episode_id"] == "ep_test_001"
    assert d["total_steps"] == 100
    assert d["success_label"] is True


def test_timestep_dataclass():
    step = Timestep(
        step_index=0,
        timestamp=0.0,
        joint_positions=[0.0] * 6,
        joint_velocities=[0.0] * 6,
        joint_efforts=[0.0] * 6,
        gripper_stroke=0.02,
        tcp_pose=TCPPose(position=[0.2, 0.0, 0.1], orientation=[0.0, 0.0, 0.0, 1.0]),
        action=[0.0] * 7,
    )
    d = step.to_dict()
    assert d["step_index"] == 0
    assert d["gripper_stroke"] == 0.02
    assert len(d["joint_positions"]) == 6
