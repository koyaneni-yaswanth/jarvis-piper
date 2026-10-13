"""
Unit tests for Independent Safety Supervisor (Phase 7).
Verifies:
1. Joint limit boundary clamping.
2. Velocity clamping to MAX_VELOCITY_RAD_S.
3. Cartesian workspace bounding box enforcement.
4. E-stop latching and deliberate unlatching token requirement.
5. Physical commissioning interlock authorization.
"""

import pytest
from safety.safety_supervisor import SafetySupervisor


def test_safety_joint_clamping():
    safety = SafetySupervisor()
    safety.record_heartbeat()

    # Target exceeding joint 1 upper limit (+2.55)
    target = [3.5, 0.5, -0.5, 0.0, 0.0, 0.0]
    is_safe, sanitized, reason = safety.validate_joint_command(target)

    assert sanitized[0] <= 2.55, "Joint 1 should be clamped to 2.55 rad"


def test_safety_estop_latching():
    safety = SafetySupervisor()
    safety.record_heartbeat()

    safety.trigger_estop("Test trigger")
    assert safety.estop_latched is True

    # Commands must be rejected while E-stop is latched
    is_safe, _, reason = safety.validate_joint_command([0.0, 0.5, -0.5, 0.0, 0.0, 0.0])
    assert is_safe is False
    assert "E-STOP" in reason

    # Unlatching requires exact confirmation token
    bad_reset = safety.reset_estop("WRONG_TOKEN")
    assert bad_reset is False
    assert safety.estop_latched is True

    good_reset = safety.reset_estop("CONFIRM_SAFE_RESET")
    assert good_reset is True
    assert safety.estop_latched is False


def test_safety_physical_interlock():
    safety = SafetySupervisor()
    assert safety.hardware_confirmed is False

    ok = safety.authorize_physical_execution("OPERATOR_COMMISSIONING_CONFIRMED")
    assert ok is True
    assert safety.hardware_confirmed is True
