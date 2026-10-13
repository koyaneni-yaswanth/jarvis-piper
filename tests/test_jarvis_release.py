"""
JARVIS-PiPER Release & Fault-Injection Acceptance Test Suite.
Validates:
- Hardware mock interfaces
- Safety supervisor fault injection (E-Stop, Clutch, Watchdog, Limits, Tracking loss, NaN)
- Demonstration recording & 7-point validation
- BC training and offline evaluation
- Supervised policy dry-run execution
"""

import os
import time
import pytest
import numpy as np

from jarvis.errors import (
    MotionNotAuthorizedError,
    EStopTriggeredError,
    ClutchReleasedError,
    TrackingLostError,
    JointLimitViolationError,
    WorkspaceViolationError,
    WatchdogTimeoutError,
)
from jarvis.hardware import MockArm, MockGripper, MockTeleop, MockCamera
from jarvis.safety import SafetySupervisor
from jarvis.teleop import TeleoperationMapper
from jarvis.record import EpisodeRecorder, EpisodeValidator
from jarvis.train import train_bc_policy, BCPolicy
from jarvis.policy import SupervisedPolicyRunner
from jarvis.doctor import JarvisDoctor


def test_doctor_diagnostics_pass():
    doc = JarvisDoctor()
    res = doc.run_diagnostics()
    assert "platform" in res
    assert "can_bus" in res
    assert res["config"]["status"] == "PASS"


def test_hardware_mock_loop():
    arm = MockArm()
    assert arm.connect() is True
    assert arm.is_connected() is True
    state = arm.get_joint_state()
    assert len(state["positions"]) == 6

    # Test joint command
    assert arm.command_joint_positions([0.1]*6) is True
    assert arm.get_joint_state()["positions"] == [0.1]*6
    arm.disconnect()
    assert arm.is_connected() is False


# -----------------------------------------------------------------------------
# Safety Supervisor Fault-Injection Tests
# -----------------------------------------------------------------------------

def test_safety_motion_gate_unauthorized():
    safety = SafetySupervisor()
    cur = [0.0, 0.5, -0.6, 0.0, 0.1, 0.0]
    cmd = [0.0, 0.52, -0.62, 0.0, 0.1, 0.0]

    # Attempting physical execution without authorization token must raise
    with pytest.raises(MotionNotAuthorizedError):
        safety.validate_and_filter(cmd, cur, clutch_engaged=True, is_hardware_target=True)

    # Authorization with token opens gate
    safety.authorize_motion("ENABLE MOTION")
    safe_q = safety.validate_and_filter(cmd, cur, clutch_engaged=True, is_hardware_target=True)
    assert len(safe_q) == 6


def test_safety_estop_latch():
    safety = SafetySupervisor()
    cur = [0.0, 0.5, -0.6, 0.0, 0.1, 0.0]
    cmd = [0.0, 0.52, -0.62, 0.0, 0.1, 0.0]

    safety.trigger_estop("Test emergency button hit")
    assert safety.is_estopped() is True

    with pytest.raises(EStopTriggeredError):
        safety.validate_and_filter(cmd, cur, clutch_engaged=True)

    # Reset requires token
    with pytest.raises(MotionNotAuthorizedError):
        safety.reset_estop("WRONG_TOKEN")

    safety.reset_estop("ENABLE MOTION")
    assert safety.is_estopped() is False


def test_safety_clutch_released():
    safety = SafetySupervisor()
    cur = [0.0, 0.5, -0.6, 0.0, 0.1, 0.0]
    cmd = [0.0, 0.52, -0.62, 0.0, 0.1, 0.0]

    # Disengaged clutch must raise ClutchReleasedError
    with pytest.raises(ClutchReleasedError):
        safety.validate_and_filter(cmd, cur, clutch_engaged=False)


def test_safety_tracking_lost():
    safety = SafetySupervisor(tracking_timeout_sec=0.05)
    cur = [0.0, 0.5, -0.6, 0.0, 0.1, 0.0]
    cmd = [0.0, 0.52, -0.62, 0.0, 0.1, 0.0]

    # Tracking age of 100 ms must trigger auto-hold
    with pytest.raises(TrackingLostError):
        safety.validate_and_filter(cmd, cur, clutch_engaged=True, tracking_age_sec=0.10)


def test_safety_joint_limits():
    safety = SafetySupervisor()
    cur = [0.0, 0.5, -0.6, 0.0, 0.1, 0.0]
    # Joint 1 max is +2.618 rad; target 3.50 rad must violate limit
    cmd = [3.50, 0.5, -0.6, 0.0, 0.1, 0.0]

    with pytest.raises(JointLimitViolationError):
        safety.validate_and_filter(cmd, cur, clutch_engaged=True)


def test_safety_nan_rejected():
    safety = SafetySupervisor()
    cur = [0.0, 0.5, -0.6, 0.0, 0.1, 0.0]
    cmd = [float("nan"), 0.5, -0.6, 0.0, 0.1, 0.0]

    with pytest.raises(ValueError):
        safety.validate_and_filter(cmd, cur, clutch_engaged=True)


def test_safety_workspace_box():
    safety = SafetySupervisor()
    cur = [0.0, 0.5, -0.6, 0.0, 0.1, 0.0]
    cmd = [0.0, 0.5, -0.6, 0.0, 0.1, 0.0]
    # ee_pos z=-0.10 m (below tabletop z=0.015 m bound)
    unsafe_ee = [0.35, 0.0, -0.10]

    with pytest.raises(WorkspaceViolationError):
        safety.validate_and_filter(cmd, cur, clutch_engaged=True, ee_pos=unsafe_ee)


def test_safety_watchdog_timeout():
    safety = SafetySupervisor(watchdog_timeout_sec=0.05)
    cur = [0.0, 0.5, -0.6, 0.0, 0.1, 0.0]
    cmd = [0.0, 0.52, -0.62, 0.0, 0.1, 0.0]

    # First call valid
    safety.validate_and_filter(cmd, cur, clutch_engaged=True)

    # Sleep past watchdog threshold
    time.sleep(0.08)

    with pytest.raises(WatchdogTimeoutError):
        safety.validate_and_filter(cmd, cur, clutch_engaged=True)


# -----------------------------------------------------------------------------
# Recording, Validation & Training Tests
# -----------------------------------------------------------------------------

def test_record_validate_roundtrip(tmp_path):
    rec = EpisodeRecorder(output_dir=str(tmp_path))
    ep_dir = rec.start_episode("ep_test_001", {"operator": "pytest"})

    for i in range(10):
        rec.record_step(
            joint_positions=[0.0, 0.5, -0.6 + 0.01 * i, 0.0, 0.1, 0.0],
            joint_velocities=[0.0]*6,
            action=[0.0, 0.5, -0.6 + 0.01 * i, 0.0, 0.1, 0.0],
            gripper_stroke=0.035,
        )
    rec.stop_episode(outcome="success")

    val = EpisodeValidator()
    res = val.validate_episode(ep_dir)
    assert res["valid"] is True
    assert res["num_steps"] == 10
    assert len(res["errors"]) == 0


def test_corrupted_episode_caught(tmp_path):
    rec = EpisodeRecorder(output_dir=str(tmp_path))
    ep_dir = rec.start_episode("ep_corrupt_001", {"operator": "pytest"})

    # Deliberately corrupt with identical timestamps
    rec.record_step([0.0, 0.5, -0.6, 0.0, 0.1, 0.0], [0.0]*6, [0.0]*6, 0.035)
    rec.steps[-1]["timestamp"] = 0.05
    rec.record_step([0.0, 0.5, -0.6, 0.0, 0.1, 0.0], [0.0]*6, [0.0]*6, 0.035)
    rec.steps[-1]["timestamp"] = 0.05  # duplicate / non-monotonic
    rec.stop_episode(outcome="failed")

    val = EpisodeValidator()
    res = val.validate_episode(ep_dir)
    assert res["valid"] is False
    assert any("Non-monotonic" in e for e in res["errors"])


def test_bc_training_and_offline_eval(tmp_path):
    meta = train_bc_policy(dataset_dirs=[], epochs=2, output_dir=str(tmp_path))
    assert "train_loss" in meta
    assert "val_loss" in meta
    assert meta["train_loss"] >= 0.0


def test_supervised_policy_dry_run(tmp_path):
    arm = MockArm()
    arm.connect()
    gripper = MockGripper()
    gripper.connect()
    safety = SafetySupervisor()
    policy = BCPolicy()

    # Mock policy to return safe nominal state
    policy.predict = lambda obs: [0.0, 0.51, -0.61, 0.0, 0.1, 0.0, 0.035]

    runner = SupervisedPolicyRunner(policy, arm, gripper, safety, log_dir=str(tmp_path))
    res = runner.execute_rollout(max_steps=10, dry_run=True)
    assert res["dry_run"] is True
    assert res["steps_executed"] == 10
    assert res["anomaly_detected"] is False

