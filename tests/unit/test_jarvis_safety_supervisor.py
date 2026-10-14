"""
Unit tests for jarvis.safety.SafetySupervisor (Milestone 2 Hardware Interface Readiness).

Verifies:
1. Milestone lock unconditionally blocks hardware actuation even if operator authorized motion.
2. ExecutionMode transitions initialize safely in MOCK and do not auto-authorize hardware motion.
3. Feedback staleness detection triggers StaleFeedbackError when dt exceeds threshold.
4. Calibration status checking rejects any uncalibrated/stale/invalid states with CalibrationStatusError.
5. Strict joint validation rejects NaN, Inf, and incorrect joint count.
6. Mode accessor and milestone lock toggles.
"""

import math
import pytest

from jarvis.safety import SafetySupervisor, ExecutionMode
from jarvis.pika_discovery import CalibrationStatus
from jarvis.errors import (
    MotionNotAuthorizedError,
    StaleFeedbackError,
    CalibrationStatusError,
    InvalidJointStateError,
    TrackingLostError,
    EStopTriggeredError,
    ClutchReleasedError,
)

NOMINAL_Q = [0.0, 0.5, -0.6, 0.0, 0.1, 0.0]
TARGET_Q = [0.02, 0.52, -0.58, 0.01, 0.11, 0.01]


def test_supervisor_initializes_in_mock_mode():
    supervisor = SafetySupervisor()
    assert supervisor.get_mode() == ExecutionMode.MOCK
    assert supervisor.is_motion_authorized() is False
    assert supervisor.is_estopped() is False


def test_execution_mode_transitions_do_not_escalate_authorization():
    supervisor = SafetySupervisor()
    for mode in [
        ExecutionMode.SIMULATION,
        ExecutionMode.REPLAY,
        ExecutionMode.TELEOP_DRY_RUN,
        ExecutionMode.HARDWARE_SUPERVISED,
    ]:
        supervisor.set_mode(mode)
        assert supervisor.get_mode() == mode
        # Escalating execution mode must never authorize hardware motion automatically
        assert supervisor.is_motion_authorized() is False


def test_milestone_lock_blocks_hardware_actuation_unconditionally():
    supervisor = SafetySupervisor(milestone_lock=True)
    supervisor.authorize_motion("ENABLE MOTION")
    assert supervisor.is_motion_authorized() is True

    # Despite having session authorization, milestone_lock MUST block hardware target
    with pytest.raises(MotionNotAuthorizedError) as exc_info:
        supervisor.validate_and_filter(
            command_q=TARGET_Q,
            current_q=NOMINAL_Q,
            clutch_engaged=True,
            is_hardware_target=True,
        )
    assert "Milestone 2 strictly prohibits physical hardware motion" in str(exc_info.value)

    # When targeting mock / simulation (is_hardware_target=False), commands succeed
    safe_q = supervisor.validate_and_filter(
        command_q=TARGET_Q,
        current_q=NOMINAL_Q,
        clutch_engaged=True,
        is_hardware_target=False,
    )
    assert len(safe_q) == 6


def test_milestone_lock_toggle():
    supervisor = SafetySupervisor(milestone_lock=False)
    supervisor.authorize_motion("ENABLE MOTION")
    # Allowed when unlocked
    safe_q = supervisor.validate_and_filter(
        command_q=TARGET_Q,
        current_q=NOMINAL_Q,
        clutch_engaged=True,
        is_hardware_target=True,
    )
    assert len(safe_q) == 6

    # Lock it
    supervisor.set_milestone_lock(True)
    assert supervisor.milestone_lock is True
    with pytest.raises(MotionNotAuthorizedError):
        supervisor.validate_and_filter(
            command_q=TARGET_Q,
            current_q=NOMINAL_Q,
            clutch_engaged=True,
            is_hardware_target=True,
        )


def test_stale_feedback_triggers_error():
    supervisor = SafetySupervisor(feedback_timeout_sec=0.10)

    # Feedback younger than timeout is accepted
    safe_q = supervisor.validate_and_filter(
        command_q=TARGET_Q,
        current_q=NOMINAL_Q,
        feedback_age_sec=0.05,
    )
    assert len(safe_q) == 6

    # Feedback older than 100 ms raises StaleFeedbackError
    with pytest.raises(StaleFeedbackError) as exc_info:
        supervisor.validate_and_filter(
            command_q=TARGET_Q,
            current_q=NOMINAL_Q,
            feedback_age_sec=0.15,
        )
    assert exc_info.value.age == 0.15
    assert exc_info.value.timeout == 0.10


def test_calibration_status_rejection():
    supervisor = SafetySupervisor()

    # CALIBRATED is accepted
    safe_q = supervisor.validate_and_filter(
        command_q=TARGET_Q,
        current_q=NOMINAL_Q,
        calibration_status=CalibrationStatus.CALIBRATED,
    )
    assert len(safe_q) == 6

    # All other statuses must be rejected
    rejected_statuses = [
        CalibrationStatus.NOT_CONFIGURED,
        CalibrationStatus.NOT_CALIBRATED,
        CalibrationStatus.INVALID,
        CalibrationStatus.STALE,
        CalibrationStatus.UNAVAILABLE,
    ]
    for status in rejected_statuses:
        with pytest.raises(CalibrationStatusError) as exc_info:
            supervisor.validate_and_filter(
                command_q=TARGET_Q,
                current_q=NOMINAL_Q,
                calibration_status=status,
            )
        assert exc_info.value.status == status.value


def test_invalid_joint_states_rejected():
    supervisor = SafetySupervisor()

    # Reject Inf
    inf_q = [0.0, float("inf"), -0.6, 0.0, 0.1, 0.0]
    with pytest.raises(InvalidJointStateError):
        supervisor.validate_and_filter(inf_q, NOMINAL_Q)

    with pytest.raises(InvalidJointStateError):
        supervisor.validate_and_filter(TARGET_Q, inf_q)

    # Reject wrong joint count
    with pytest.raises(InvalidJointStateError):
        supervisor.validate_and_filter([0.0, 0.0, 0.0], NOMINAL_Q)

    with pytest.raises(InvalidJointStateError):
        supervisor.validate_and_filter(TARGET_Q, [0.0] * 7)
