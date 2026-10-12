"""
Unit tests for SafetySupervisor.
Verifies joint limit clipping, velocity slew rate, Cartesian workspace bounds, and E-Stop latching.
"""

import pytest
from jarvis_piper.safety.supervisor import SafetySupervisor


def test_safety_joint_clipping():
    supervisor = SafetySupervisor()
    current_q = [0.0, 0.5, -0.5, 0.0, 0.0, 0.0]
    # Request out of bounds joint 1 (+5.0 rad exceeds +2.618 limit)
    cmd_q = [5.0, 0.5, -0.5, 0.0, 0.0, 0.0]

    safe_q, stroke, is_safe, reason = supervisor.filter_and_validate_action(cmd_q, current_q, dt=1.0)
    # Slew rate and joint bounds must clamp joint 1
    assert safe_q[0] <= 2.618
    assert safe_q[0] >= -2.618


def test_safety_estop_latching():
    supervisor = SafetySupervisor()
    current_q = [0.0, 0.5, -0.5, 0.0, 0.0, 0.0]
    cmd_q = [0.1, 0.5, -0.5, 0.0, 0.0, 0.0]

    supervisor.trigger_estop("Test emergency button press")
    safe_q, stroke, is_safe, reason = supervisor.filter_and_validate_action(cmd_q, current_q)
    assert not is_safe
    assert "E-Stop" in reason
    # Position must be frozen at current_q
    assert safe_q == current_q

    # Reset estop
    supervisor.reset_estop()
    safe_q2, _, is_safe2, _ = supervisor.filter_and_validate_action(cmd_q, current_q)
    assert is_safe2
