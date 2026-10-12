import numpy as np
import pytest

from jarvis_piper.perception.detector import JarvisPerceptionDetector


def test_perception_deprojection():
    detector = JarvisPerceptionDetector()
    p_cam = detector.deproject_pixel_to_camera_point(320.0, 240.0, 0.60)
    assert pytest.approx(p_cam[0], abs=1e-3) == 0.0
    assert pytest.approx(p_cam[1], abs=1e-3) == 0.0
    assert pytest.approx(p_cam[2], abs=1e-3) == 0.60


def test_perception_detection_and_localization():
    detector = JarvisPerceptionDetector()
    dets = detector.detect_objects()
    assert len(dets) >= 2
    names = [d["name"] for d in dets]
    assert "red block" in names or "bowl" in names

    target_pos, dest_pos = detector.localize_target_and_destination("red block", "bowl")
    assert len(target_pos) == 3
    assert len(dest_pos) == 3
    # Both should be in front of robot (x > 0.1) and above tabletop (z > 0.0)
    assert target_pos[0] > 0.1
    assert target_pos[2] > 0.01
    assert dest_pos[0] > 0.1
    assert dest_pos[2] > 0.01
