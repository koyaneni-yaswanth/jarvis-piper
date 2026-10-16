"""
Unit and integration tests for Live Observation Recorder, Validator, and Replayer.
Uses strictly labeled synthetic / mocked fixtures to test hardware-recorder lifecycle,
schema validation, timestamp monotonicity, error detection, and HDF5 export.
"""

import os
import json
import tempfile
import pytest
import numpy as np
from pathlib import Path
from unittest.mock import MagicMock, patch

from jarvis.live_recorder import LiveObservationRecorder
from tools.live_validate import validate_recording_session
from tools.live_replay import LiveObservationReplayer, HAS_H5PY


@pytest.fixture
def mock_recorded_session(tmp_path):
    """Creates a well-formed synthetic live recording session directory."""
    session_dir = tmp_path / "live_obs_synthetic_test"
    session_dir.mkdir(parents=True)

    wrist_dir = session_dir / "wrist_color"
    depth_dir = session_dir / "wrist_depth"
    overhead_dir = session_dir / "overhead_color"
    wrist_dir.mkdir()
    depth_dir.mkdir()
    overhead_dir.mkdir()

    # Import cv2 to generate small test images if available
    try:
        import cv2
        has_cv = True
    except ImportError:
        has_cv = False

    n_steps = 15
    fps = 30.0
    dt = 1.0 / fps

    telemetry_path = session_dir / "telemetry.jsonl"
    with open(telemetry_path, "w", encoding="utf-8") as telem_f:
        for i in range(n_steps):
            t_s = round(i * dt, 4)
            t_ns = int(i * dt * 1e9) + 1_000_000_000

            rec = {
                "step": i,
                "timestamp_s": t_s,
                "monotonic_ns": t_ns,
                "wall_ns": 1_700_000_000_000_000_000 + t_ns,
                "joint_positions": [0.01 * i, -0.05, 0.1, 0.0, 0.2, -0.1],
                "tcp_pose": {
                    "position_m": [0.35, 0.0, 0.25],
                    "rpy_rad": [0.0, 1.57, 0.0],
                },
                "gripper_stroke_m": 0.04,
                "arm_status": "NORMAL(0x0)",
                "arm_mode": "ROBOT_STATUS_OFFLINE",
                "pika_sense": {
                    "encoder_angle_deg": 90.0,
                    "encoder_rad": 1.57,
                    "gripper_distance_mm": 50.0,
                    "command_trigger_state": 0,
                },
                "wrist_color_file": f"wrist_color/frame_{i:05d}.jpg",
                "wrist_depth_file": f"wrist_depth/depth_{i:05d}.png",
                "overhead_color_file": f"overhead_color/overhead_{i:05d}.jpg",
            }
            telem_f.write(json.dumps(rec) + "\n")

            if has_cv:
                dummy_color = np.full((120, 160, 3), 128, dtype=np.uint8)
                dummy_depth = np.full((120, 160), 500, dtype=np.uint16)  # 500 mm
                cv2.imwrite(str(wrist_dir / f"frame_{i:05d}.jpg"), dummy_color)
                cv2.imwrite(str(depth_dir / f"depth_{i:05d}.png"), dummy_depth)
                cv2.imwrite(str(overhead_dir / f"overhead_{i:05d}.jpg"), dummy_color)
            else:
                (wrist_dir / f"frame_{i:05d}.jpg").write_bytes(b"mock_jpg")
                (depth_dir / f"depth_{i:05d}.png").write_bytes(b"mock_png")
                (overhead_dir / f"overhead_{i:05d}.jpg").write_bytes(b"mock_jpg")

    meta = {
        "session_id": "live_obs_synthetic_test",
        "task_description": "Synthetic unit test session",
        "operator": "test_operator",
        "created_at_utc": "2026-10-16T10:00:00Z",
        "target_control_hz": fps,
        "actual_duration_seconds": round(n_steps * dt, 3),
        "total_timesteps": n_steps,
        "effective_hz": fps,
        "streams_recorded": {
            "robot_telemetry": {"samples": n_steps, "hz": fps},
            "realsense_d405": {"color_frames": n_steps, "depth_frames": n_steps, "hz": fps},
            "overhead_camera": {"frames": n_steps, "hz": fps},
            "pika_sense": {"samples": n_steps, "hz": fps},
        },
        "dropped_samples": 0,
        "verification_status": "SYNTHETIC_TEST_FIXTURE",
    }
    with open(session_dir / "metadata.json", "w", encoding="utf-8") as meta_f:
        json.dump(meta, meta_f, indent=2)

    return session_dir


def test_validator_on_valid_session(mock_recorded_session):
    """Ensures validator certifies well-formed session with all streams."""
    report = validate_recording_session(mock_recorded_session)
    assert report["valid"] is True, f"Validation failed with errors: {report.get('errors')}"
    assert report["metrics"]["total_steps"] == 15
    assert report["streams_verified"]["robot_telemetry"] is True
    assert report["streams_verified"]["realsense_wrist_color"] is True
    assert report["streams_verified"]["realsense_wrist_depth"] is True
    assert report["streams_verified"]["overhead_camera"] is True
    assert report["streams_verified"]["pika_sense"] is True
    assert len(report["errors"]) == 0


def test_validator_detects_non_monotonic_timestamps(tmp_path):
    """Ensures validator rejects non-monotonic timestamps."""
    bad_dir = tmp_path / "bad_session"
    bad_dir.mkdir()

    meta = {"session_id": "bad_session", "target_control_hz": 30.0}
    (bad_dir / "metadata.json").write_text(json.dumps(meta))

    records = [
        {"step": 0, "timestamp_s": 0.0, "monotonic_ns": 1000},
        {"step": 1, "timestamp_s": 0.05, "monotonic_ns": 2000},
        {"step": 2, "timestamp_s": 0.04, "monotonic_ns": 1900},  # Time went backwards!
    ]
    with open(bad_dir / "telemetry.jsonl", "w") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")

    report = validate_recording_session(bad_dir)
    assert report["valid"] is False
    assert any("Non-monotonic" in err for err in report["errors"])


def test_validator_detects_missing_image_files(tmp_path):
    """Ensures validator flags referenced files that do not exist."""
    missing_dir = tmp_path / "missing_files_session"
    missing_dir.mkdir()

    meta = {"session_id": "missing_files_session", "target_control_hz": 30.0}
    (missing_dir / "metadata.json").write_text(json.dumps(meta))

    records = [
        {
            "step": 0,
            "timestamp_s": 0.0,
            "monotonic_ns": 1000,
            "wrist_color_file": "wrist_color/missing_frame_000.jpg",
        }
    ]
    with open(missing_dir / "telemetry.jsonl", "w") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")

    report = validate_recording_session(missing_dir)
    assert report["valid"] is False
    assert any("missing from disk" in err for err in report["errors"])


def test_replayer_summary_and_stream(mock_recorded_session):
    """Tests LiveObservationReplayer summary generation and step iteration."""
    replayer = LiveObservationReplayer(mock_recorded_session)
    assert replayer.total_steps == 15

    summary = replayer.get_summary()
    assert summary["total_steps"] == 15
    assert "robot_joints" in summary["modalities"]
    assert summary["modalities"]["wrist_color_frames"] == 15

    # Test playback streaming with zero delay
    streamed_steps = list(replayer.stream_steps(playback_speed=0))
    assert len(streamed_steps) == 15
    assert streamed_steps[0]["step"] == 0
    assert streamed_steps[-1]["step"] == 14


def test_replayer_hdf5_export(mock_recorded_session, tmp_path):
    """Tests exporting live session to HDF5."""
    if not HAS_H5PY:
        pytest.skip("h5py not installed in test environment")

    replayer = LiveObservationReplayer(mock_recorded_session)
    h5_path = tmp_path / "exported_session.h5"
    out = replayer.export_to_hdf5(h5_path)

    assert out.is_file()
    assert out.stat().st_size > 0

    import h5py

    with h5py.File(str(out), "r") as h5:
        assert "observations/joint_positions" in h5
        assert h5["observations/joint_positions"].shape == (15, 6)
        assert "observations/gripper_stroke_m" in h5
        assert "timestamps" in h5
        assert h5.attrs["session_id"] == "live_obs_synthetic_test"


def test_live_recorder_graceful_missing_hardware(tmp_path):
    """Ensures LiveObservationRecorder handles missing hardware safely without crashing."""
    recorder = LiveObservationRecorder(
        output_dir=str(tmp_path),
        can_port="can_nonexistent",
        realsense_enabled=False,
        overhead_camera_index=999,
        pika_serial_port="/dev/tty_nonexistent",
        pika_enabled=False,
    )
    status = recorder.initialize_hardware()
    assert isinstance(status, dict)
    assert status["can_bus"] is False
    assert status["piper_telemetry"] is False
    assert status["realsense_d405"] is False
    assert status["overhead_camera"] is False
    assert status["pika_sense"] is False
    recorder.close()


def test_live_recorder_mock_record_session(tmp_path):
    """Ensures LiveObservationRecorder records properly when hardware interfaces return data."""
    recorder = LiveObservationRecorder(
        output_dir=str(tmp_path),
        target_control_hz=50.0,
        realsense_enabled=False,
        overhead_camera_index=None,
        pika_enabled=False,
    )

    # Mock PiPER interface
    mock_piper = MagicMock()
    mock_jmsg = MagicMock()
    for i in range(1, 7):
        setattr(mock_jmsg.joint_state, f"joint_{i}", 1000 * i)  # 1.0 deg * i
    mock_piper.GetArmJointMsgs.return_value = mock_jmsg

    mock_ep = MagicMock()
    mock_ep.end_pose.X_axis = 100000
    mock_ep.end_pose.Y_axis = 200000
    mock_ep.end_pose.Z_axis = 300000
    mock_ep.end_pose.RX_axis = 0
    mock_ep.end_pose.RY_axis = 0
    mock_ep.end_pose.RZ_axis = 0
    mock_piper.GetArmEndPoseMsgs.return_value = mock_ep

    mock_grp = MagicMock()
    mock_grp.gripper_state.grippers_angle = 35000  # 0.035m
    mock_piper.GetArmGripperMsgs.return_value = mock_grp

    mock_st = MagicMock()
    mock_st.arm_status.arm_status = "NORMAL(0x0)"
    mock_st.arm_status.ctrl_mode = "STANDBY"
    mock_piper.GetArmStatus.return_value = mock_st

    recorder.piper = mock_piper

    session_dir = recorder.record_session(duration_seconds=0.1, task_description="Unit test mock record")
    assert session_dir.is_dir()
    assert (session_dir / "metadata.json").is_file()
    assert (session_dir / "telemetry.jsonl").is_file()

    # Verify session via validator
    report = validate_recording_session(session_dir)
    assert report["valid"] is True
    assert report["streams_verified"]["robot_telemetry"] is True
    assert report["metrics"]["total_steps"] >= 3


def test_live_recorder_with_action_provider(tmp_path):
    """Ensures LiveObservationRecorder correctly logs operator actions from action provider."""
    mock_action_provider = MagicMock()
    mock_action_provider.get_latest_action.return_value = {
        "type": "cartesian_target",
        "values": [0.35, 0.05, 0.20, 0.0, 0.0, 0.0, 1.0],
        "gripper_stroke_m": 0.030,
        "source": "pika_teleop",
    }

    recorder = LiveObservationRecorder(
        output_dir=str(tmp_path),
        target_control_hz=50.0,
        realsense_enabled=False,
        overhead_camera_index=None,
        pika_enabled=False,
        action_provider=mock_action_provider,
    )

    session_dir = recorder.record_session(
        duration_seconds=0.1,
        task_description="Action logging test",
        episode_mode=True,
        task_name="pick_cube",
    )
    assert session_dir.is_dir()
    assert "pick_cube" in str(session_dir)

    report = validate_recording_session(session_dir)
    assert report["valid"] is True
    assert report["streams_verified"]["operator_actions"] is True
    assert report["metrics"]["action_samples"] >= 3
