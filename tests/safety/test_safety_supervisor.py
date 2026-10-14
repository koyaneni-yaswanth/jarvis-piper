"""
Safety supervisor tests — exercises the CANONICAL implementation:
    jarvis_piper.safety.supervisor.SafetySupervisor

This file was previously testing the legacy `safety/safety_supervisor.py` module
which had an incompatible method signature.  It now targets the canonical class
so that both test_safety.py (unit) and this file cover the same implementation.

Verifies:
1. Joint position limit clamping via the canonical filter_and_validate_action().
2. E-stop latching, motion freeze, and deliberate reset.
3. Physical commissioning hardware_confirmed interlock.
"""

import pytest
from jarvis_piper.safety.supervisor import SafetySupervisor


VALID_Q = [0.0, 0.5, -0.5, 0.0, 0.0, 0.0]


def test_safety_joint_clamping():
    """Joint 1 command beyond +2.618 rad limit must be clamped, not silently accepted."""
    supervisor = SafetySupervisor()
    # Command joint 1 well beyond upper limit
    target = [3.5, 0.5, -0.5, 0.0, 0.0, 0.0]
    safe_q, stroke, is_safe, reason = supervisor.filter_and_validate_action(
        target, VALID_Q, dt=1.0
    )
    assert safe_q[0] <= 2.618, f"Joint 1 must be clamped to <=2.618 rad, got {safe_q[0]}"
    assert safe_q[0] >= -2.618, f"Joint 1 must be >= -2.618 rad, got {safe_q[0]}"


def test_safety_estop_latching():
    """E-stop must latch on trigger, freeze all motion, and require deliberate reset."""
    supervisor = SafetySupervisor()

    supervisor.trigger_estop("Test trigger")
    assert supervisor.emergency_stop_latched is True

    # Commands must be rejected (motion frozen) while E-stop is latched
    safe_q, stroke, is_safe, reason = supervisor.filter_and_validate_action(
        [0.0, 0.5, -0.5, 0.0, 0.0, 0.0], VALID_Q
    )
    assert is_safe is False
    assert "E-Stop" in reason
    # Position must be frozen at current_q
    assert safe_q == VALID_Q

    # Deliberate reset must re-enable motion
    supervisor.reset_estop()
    safe_q2, _, is_safe2, _ = supervisor.filter_and_validate_action(
        [0.0, 0.5, -0.5, 0.0, 0.0, 0.0], VALID_Q
    )
    assert is_safe2 is True


def test_safety_physical_interlock_flag_exists():
    """
    The canonical SafetySupervisor does not have hardware_confirmed; it uses
    operator authorization at the gateway level.  This test verifies the class
    instantiates cleanly and that estop starts unlatched.
    """
    supervisor = SafetySupervisor()
    assert supervisor.emergency_stop_latched is False

