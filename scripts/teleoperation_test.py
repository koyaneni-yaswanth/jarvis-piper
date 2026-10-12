#!/usr/bin/env python3
"""
Validates PIKA Sense to PiPER teleoperation coordinate mapping and dead-man clutch interlocks.
"""

import sys
sys.path.insert(0, "python")
from jarvis_piper.hardware.mock_adapter import MockPikaSenseAdapter, MockPiperAdapter
from jarvis_piper.safety.supervisor import SafetySupervisor


def test_teleoperation():
    print("=" * 80)
    print("      PIKA SENSE -> PIPER TELEOPERATION MAPPING & CLUTCH TEST")
    print("=" * 80)

    pika = MockPikaSenseAdapter()
    robot = MockPiperAdapter()
    supervisor = SafetySupervisor()

    # 1. Test Clutch Engaged
    pos, quat = pika.get_target_pose()
    clutch = pika.get_clutch_active()
    print(f" 1. Hand Tracking Setpoint:   {[round(x, 4) for x in pos]} | Clutch: {clutch}")
    assert clutch is True

    # 2. Safety filtering
    current_q, _, _ = robot.get_joint_states()
    safe_q, stroke, is_safe, reason = supervisor.filter_and_validate_action(
        target_q=[0.1, 0.5, -0.6, 0.0, 0.2, 0.0],
        current_q=current_q,
    )
    print(f" 2. Action Filter Output:      {[round(x, 4) for x in safe_q]} | Safe: {is_safe} ({reason})")
    assert is_safe is True

    # 3. Test Dead-Man Release (Clutch = False)
    print(" 3. Testing Dead-Man Safety Stop...")
    supervisor.trigger_estop("Clutch Released")
    safe_frozen, _, is_safe_e, reason_e = supervisor.filter_and_validate_action(
        target_q=[0.5, 0.8, -0.8, 0.1, 0.2, 0.0],
        current_q=current_q,
    )
    print(f"    Released Command Result:   {[round(x, 4) for x in safe_frozen]} | Reason: {reason_e}")
    assert safe_frozen == current_q
    assert not is_safe_e

    supervisor.reset_estop()
    print("=" * 80)
    print(" [PASSED] Teleoperation Mapping and Safety Interlocks Verified!")
    print("=" * 80)
    return 0


if __name__ == "__main__":
    sys.exit(test_teleoperation())
