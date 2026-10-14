"""
Unit tests for jarvis.config_validator.ConfigValidator.
Verifies safety boundary enforcement on robot configuration files.
"""

import pytest
from jarvis.config_validator import ConfigValidator


def test_nominal_config_validates():
    report = ConfigValidator.validate_file("config.yaml")
    assert report["valid"] is True
    assert len(report["errors"]) == 0


def test_missing_config_fails():
    report = ConfigValidator.validate_file("non_existent_config.yaml")
    assert report["valid"] is False
    assert any("not found" in err for err in report["errors"])


def test_illegal_can_bitrate_rejected():
    bad_cfg = {
        "robot": {"bitrate": 500000},
        "safety": {
            "speed_scale": 0.10,
            "max_joint_velocity_rad_s": 1.50,
            "workspace_box": {"x": [0.1, 0.6], "y": [-0.4, 0.4], "z": [0.01, 0.5]},
        },
    }
    report = ConfigValidator.validate_dict(bad_cfg)
    assert report["valid"] is False
    assert any("bitrate" in err for err in report["errors"])


def test_excessive_speed_scale_rejected():
    bad_cfg = {
        "robot": {"bitrate": 1000000},
        "safety": {
            "speed_scale": 0.50,  # Exceeds 0.20 conservative ceiling
            "max_joint_velocity_rad_s": 1.50,
            "workspace_box": {"x": [0.1, 0.6], "y": [-0.4, 0.4], "z": [0.01, 0.5]},
        },
    }
    report = ConfigValidator.validate_dict(bad_cfg)
    assert report["valid"] is False
    assert any("speed_scale" in err for err in report["errors"])


def test_inverted_workspace_bounds_rejected():
    bad_cfg = {
        "robot": {"bitrate": 1000000},
        "safety": {
            "speed_scale": 0.10,
            "max_joint_velocity_rad_s": 1.50,
            "workspace_box": {"x": [0.6, 0.1], "y": [-0.4, 0.4], "z": [0.01, 0.5]},  # x min > max
        },
    }
    report = ConfigValidator.validate_dict(bad_cfg)
    assert report["valid"] is False
    assert any("bounds for axis 'x'" in err for err in report["errors"])
