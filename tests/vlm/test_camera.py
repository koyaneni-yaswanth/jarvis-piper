"""
Tests for Camera Source Abstraction Layer.
"""

import pytest
import numpy as np

from jarvis_piper.perception.camera import (
    CameraSource,
    CameraFrame,
    ColorFormat,
    CameraNotOpenError,
    CameraUnavailableError,
    MockCamera,
    RecordedCamera,
    build_camera_source,
)


def test_camera_frame_validation():
    # Valid frame
    img = np.zeros((480, 640, 3), dtype=np.uint8)
    depth = np.zeros((480, 640), dtype=np.uint16)
    frame = CameraFrame(color_image=img, depth_image=depth, width=640, height=480)
    assert frame.is_valid
    assert frame.has_depth

    # Invalid / empty frame
    empty_frame = CameraFrame()
    assert not empty_frame.is_valid
    assert not empty_frame.has_depth


def test_mock_camera_lifecycle():
    cam = MockCamera(width=320, height=240, color_bgr=(100, 150, 200), depth_mm=400)
    assert not cam.is_open

    # Calling read before open raises CameraNotOpenError
    with pytest.raises(CameraNotOpenError):
        cam.read()

    cam.open()
    assert cam.is_open

    frame = cam.read()
    assert frame.is_valid
    assert frame.has_depth
    assert frame.width == 320
    assert frame.height == 240
    assert frame.color_image.shape == (240, 320, 3)
    assert frame.depth_image.shape == (240, 320)
    assert frame.frame_id == 0

    frame2 = cam.read()
    assert frame2.frame_id == 1

    cam.close()
    assert not cam.is_open


def test_mock_camera_context_manager():
    with MockCamera(width=160, height=120) as cam:
        assert cam.is_open
        frame = cam.read()
        assert frame.is_valid
    assert not cam.is_open


def test_build_camera_source_factory():
    cam = build_camera_source({"type": "mock", "width": 640, "height": 480})
    assert isinstance(cam, MockCamera)
    assert cam.width == 640

    with pytest.raises(ValueError):
        build_camera_source({"type": "invalid_camera_type"})
