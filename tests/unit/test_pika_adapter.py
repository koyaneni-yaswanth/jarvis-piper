"""
Unit tests for AgileX PIKA Sense Discovery, Calibration & Tracking Validator (Milestone 2).
Verifies:
1. Non-destructive device discovery without altering udev or system state.
2. Calibration status parsing: NOT_CONFIGURED, NOT_CALIBRATED, CALIBRATED, INVALID, STALE.
3. Tracking packet validation: freshness (<50 ms), finite values, quaternion norm.
4. Coordinate frame enforcement (FLU gripper-centered frame).
5. Strict rejection of uncalibrated identity transform fallbacks.
6. RealPikaSense error handling when hardware dongle is missing.
"""

import os
import json
import time
import pytest

from jarvis.pika_discovery import (
    PikaDiscovery,
    PikaDeviceReport,
    CalibrationStatus,
    TrackingValidator,
)
from jarvis.hardware import RealPikaSense
from jarvis.errors import DeviceNotFoundError


def test_pika_discovery_missing_dongle(tmp_path):
    """When SteamVR dongle is absent, discovery reports clean NOT_DETECTED status."""
    dummy_config = tmp_path / "nonexistent_config.json"
    report = PikaDiscovery.discover(config_path=str(dummy_config))

    assert isinstance(report, PikaDeviceReport)
    assert report.detected is False
    assert report.tracking_status == "NOT_DETECTED"
    assert report.calibration_status == CalibrationStatus.NOT_CONFIGURED
    assert len(report.error_flags) > 0


def test_pika_calibration_status_levels(tmp_path):
    """Verifies that all 5 calibration levels are accurately parsed from disk artifacts."""
    conf_file = tmp_path / "survive_config.json"

    # 1. NOT_CONFIGURED: File does not exist
    rep1 = PikaDiscovery.discover(config_path=str(tmp_path / "missing.json"))
    assert rep1.calibration_status == CalibrationStatus.NOT_CONFIGURED

    # 2. INVALID: Malformed JSON
    conf_file.write_text("{ this is malformed json :", encoding="utf-8")
    rep2 = PikaDiscovery.discover(config_path=str(conf_file))
    assert rep2.calibration_status == CalibrationStatus.INVALID

    # 3. NOT_CALIBRATED: JSON valid but empty lighthouses
    conf_file.write_text(json.dumps({"Lighthouses": {}}), encoding="utf-8")
    rep3 = PikaDiscovery.discover(config_path=str(conf_file))
    assert rep3.calibration_status == CalibrationStatus.NOT_CALIBRATED

    # 4. CALIBRATED: JSON valid with calibrated lighthouse entry
    conf_file.write_text(
        json.dumps({
            "Lighthouses": {
                "LH-001": {"pos": [1.2, 0.5, 2.1], "rot": [0.0, 0.0, 0.0, 1.0]}
            }
        }),
        encoding="utf-8"
    )
    rep4 = PikaDiscovery.discover(config_path=str(conf_file))
    assert rep4.calibration_status == CalibrationStatus.CALIBRATED

    # 5. STALE: File mtime > 30 days old
    old_mtime = time.time() - (35 * 86400)
    os.utime(str(conf_file), (old_mtime, old_mtime))
    rep5 = PikaDiscovery.discover(config_path=str(conf_file))
    assert rep5.calibration_status == CalibrationStatus.STALE


def test_tracking_validator_criteria():
    """Verifies all rejection criteria in TrackingValidator."""
    pos = [0.45, -0.08, 0.32]
    quat = [0.0, 0.0, 0.0, 1.0]

    # Valid tracking packet
    ok, errs = TrackingValidator.validate_tracking_data(
        pos, quat, frame_id="pika_gripper_frame", calibration_status=CalibrationStatus.CALIBRATED, tracking_age_sec=0.02
    )
    assert ok is True
    assert len(errs) == 0

    # Stale tracking (> 50 ms)
    ok_stale, errs_stale = TrackingValidator.validate_tracking_data(
        pos, quat, tracking_age_sec=0.06
    )
    assert ok_stale is False
    assert any("stale" in e for e in errs_stale)

    # Uncalibrated tracking
    ok_uncal, errs_uncal = TrackingValidator.validate_tracking_data(
        pos, quat, calibration_status=CalibrationStatus.NOT_CALIBRATED
    )
    assert ok_uncal is False
    assert any("not calibrated" in e for e in errs_uncal)

    # NaN in position
    ok_nan, errs_nan = TrackingValidator.validate_tracking_data(
        [float("nan"), 0.0, 0.0], quat
    )
    assert ok_nan is False
    assert any("NaN" in e for e in errs_nan)

    # Unnormalized quaternion (norm = 2.0)
    ok_quat, errs_quat = TrackingValidator.validate_tracking_data(
        pos, [0.0, 0.0, 0.0, 2.0]
    )
    assert ok_quat is False
    assert any("unnormalized" in e for e in errs_quat)

    # Unrecognized coordinate frame
    ok_frame, errs_frame = TrackingValidator.validate_tracking_data(
        pos, quat, frame_id="unregistered_custom_frame"
    )
    assert ok_frame is False
    assert any("coordinate frame" in e for e in errs_frame)

    # Rejection of uncalibrated identity transform
    ok_ident, errs_ident = TrackingValidator.validate_tracking_data(
        [0.0, 0.0, 0.0], [0.0, 0.0, 0.0, 1.0], calibration_status=CalibrationStatus.NOT_CONFIGURED
    )
    assert ok_ident is False
    assert any("identity transform" in e for e in errs_ident)


def test_real_pika_sense_missing_dongle(tmp_path):
    """RealPikaSense must fail cleanly with DeviceNotFoundError when dongle is absent."""
    sensor = RealPikaSense(config_path=str(tmp_path / "missing.json"))
    assert sensor.is_connected() is False
    assert sensor.get_tracking_age() == float("inf")

    with pytest.raises(DeviceNotFoundError) as exc_info:
        sensor.connect()

    assert "SteamVR" in str(exc_info.value)
    assert sensor.is_connected() is False
