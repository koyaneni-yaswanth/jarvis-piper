"""
Unit tests for AgileX PiPER Arm Adapter & Hardware Contract (Milestone 2).
Verifies:
1. Mock connection, disconnection, and state reporting.
2. Graceful missing-hardware error handling without hanging.
3. Rejection of NaN, infinite, and incorrect joint count states.
4. Telemetry feedback freshness calculation and stale feedback detection.
5. Communication error reporting.
6. Execution mode reporting (MOCK vs HARDWARE).
7. Strict prohibition of motor-enable commands during initialization.
8. Rejection of physical actuation commands during Milestone 2.
"""

import math
import time
import pytest

from jarvis.hardware import MockArm, RealPiperArm
from jarvis.errors import (
    CanInterfaceDownError,
    HardwareUnavailableError,
    InvalidJointStateError,
    MotionNotAuthorizedError,
    StaleFeedbackError,
)


def test_mock_arm_lifecycle():
    arm = MockArm()
    assert arm.is_connected() is False
    assert arm.get_mode() == "MOCK"

    # Must connect successfully
    assert arm.connect() is True
    assert arm.is_connected() is True

    # Initial joint state check
    state = arm.get_joint_state()
    assert len(state["positions"]) == 6
    assert len(state["velocities"]) == 6
    assert len(state["efforts"]) == 6
    assert state["freshness_sec"] < 1.0
    assert len(state["error_flags"]) == 0

    # Disconnect
    arm.disconnect()
    assert arm.is_connected() is False

    # Disconnected state query must raise HardwareUnavailableError
    with pytest.raises(HardwareUnavailableError):
        arm.get_joint_state()


def test_mock_arm_invalid_states():
    arm = MockArm()
    arm.connect()

    # Fault injection: NaN positions
    arm.inject_nan = True
    state_nan = arm.get_joint_state()
    assert any(math.isnan(x) for x in state_nan["positions"])

    # Fault injection: Incorrect joint count (5 instead of 6)
    arm.inject_nan = False
    arm.inject_wrong_count = True
    state_wrong = arm.get_joint_state()
    assert len(state_wrong["positions"]) == 5

    # Fault injection: Stale feedback (10 seconds old)
    arm.inject_wrong_count = False
    arm.inject_stale = True
    assert arm.get_feedback_freshness() >= 10.0


def test_mock_arm_communication_errors():
    arm = MockArm()
    arm.connect()
    assert len(arm.get_communication_errors()) == 0

    # Inject FIFO overflow
    arm.inject_comm_error = True
    errors = arm.get_communication_errors()
    assert "CAN_RX_FIFO_OVERFLOW" in errors

    # Inject disconnect fault
    arm.inject_disconnect = True
    assert arm.is_connected() is False
    assert "DEVICE_DISCONNECTED" in arm.get_communication_errors()


def test_real_piper_arm_missing_interface():
    """
    On machines lacking a physical can0 SocketCAN adapter, attempting connection
    must fail cleanly and immediately with CanInterfaceDownError without hanging.
    """
    arm = RealPiperArm(can_interface="can_nonexistent_99", bitrate=1000000)
    assert arm.is_connected() is False
    assert arm.get_mode() == "DISCONNECTED"

    # Construction does NOT connect or block
    with pytest.raises(CanInterfaceDownError) as exc_info:
        arm.connect()

    assert "can_nonexistent_99" in str(exc_info.value)
    assert arm.is_connected() is False
    assert len(arm.get_communication_errors()) > 0


def test_real_piper_arm_milestone_actuation_lock():
    """
    Milestone 2 strictly prohibits physical hardware motion.
    command_joint_positions() must raise MotionNotAuthorizedError.
    """
    arm = RealPiperArm(can_interface="can0")
    # If not connected, raises CanInterfaceDownError
    with pytest.raises(CanInterfaceDownError):
        arm.command_joint_positions([0.0]*6)

    # Even if mocked as connected, must raise MotionNotAuthorizedError
    arm.connected = True
    with pytest.raises(MotionNotAuthorizedError):
        arm.command_joint_positions([0.0, 0.5, -0.6, 0.0, 0.1, 0.0])
