"""
Unit tests for Hardware Abstraction Layer (HAL) adapters.
"""

import numpy as np
import pytest
from jarvis_piper.hardware.mock_adapter import (
    MockPiperAdapter,
    MockCameraAdapter,
    MockPikaSenseAdapter,
    MockGripperAdapter,
)


def test_mock_piper_adapter():
    adapter = MockPiperAdapter()
    assert adapter.connect() is True
    assert adapter.is_connected() is True

    q, v, eff = adapter.get_joint_states()
    assert len(q) == 6
    assert len(v) == 6
    assert len(eff) == 6

    # Test joint command
    cmd = [0.1, -0.2, 0.3, 0.0, 0.1, 0.0]
    assert adapter.command_joint_position(cmd) is True

    # Test TCP pose
    pos, quat = adapter.get_tcp_pose()
    assert len(pos) == 3
    assert len(quat) == 4
    # Norm of quaternion should be approximately 1.0
    assert np.isclose(np.linalg.norm(quat), 1.0, atol=1e-3)

    adapter.disconnect()
    assert adapter.is_connected() is False


def test_mock_camera_adapter():
    adapter = MockCameraAdapter(width=320, height=240)
    assert adapter.connect() is True

    rgb = adapter.get_rgb_frame()
    assert rgb is not None
    assert rgb.shape == (240, 320, 3)
    assert rgb.dtype == np.uint8

    depth = adapter.get_depth_frame()
    assert depth is not None
    assert depth.shape == (240, 320)
    assert depth.dtype == np.uint16

    adapter.disconnect()


def test_mock_gripper_adapter():
    adapter = MockGripperAdapter(stroke_max=0.035)
    assert adapter.connect() is True

    assert adapter.get_stroke() >= 0.0
    assert adapter.command_stroke(0.02) is True
    assert np.isclose(adapter.get_stroke(), 0.02, atol=1e-4)

    # Command beyond limits should clamp safely
    adapter.command_stroke(0.05)
    assert adapter.get_stroke() <= 0.035

    adapter.disconnect()


def test_mock_pika_sense_adapter():
    adapter = MockPikaSenseAdapter()
    assert adapter.connect() is True

    pos, quat = adapter.get_master_pose()
    assert len(pos) == 3
    assert len(quat) == 4

    trigger = adapter.get_trigger_stroke()
    assert 0.0 <= trigger <= 1.0

    btn = adapter.get_button_state("record")
    assert isinstance(btn, bool)

    adapter.disconnect()
