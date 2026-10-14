"""
JARVIS-PiPER: PIKA Device Discovery & Optical Tracking Validator (Milestone 2).
Provides non-destructive USB/serial discovery and rigorous validation of tracking data
without modifying any system configuration, udev rules, or device permissions.
"""

import os
import json
import time
import math
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, Any, List, Tuple, Optional
import subprocess

from jarvis.errors import CalibrationStatusError, TrackingLostError, DeviceNotFoundError


class CalibrationStatus(str, Enum):
    """AgileX PIKA & Lighthouse Calibration States."""
    NOT_CONFIGURED = "NOT_CONFIGURED"   # Config file missing
    NOT_CALIBRATED = "NOT_CALIBRATED"   # Config present but missing lighthouse geometry
    CALIBRATED = "CALIBRATED"           # Verified base station spatial matrix
    INVALID = "INVALID"                 # Malformed / unparseable calibration artifact
    STALE = "STALE"                     # Calibration expired or base stations shifted
    UNAVAILABLE = "UNAVAILABLE"         # Tracking subsystem offline / unreachable


@dataclass
class PikaDeviceReport:
    """Non-destructive hardware detection report for PIKA Sense & Stations."""
    expected_device_type: str = "PIKA Sense 6-DOF Spatial Controller"
    detected: bool = False
    usb_vendor_id: Optional[str] = None
    usb_product_id: Optional[str] = None
    device_node: Optional[str] = None
    driver_package: Optional[str] = None
    tracking_status: str = "NOT_DETECTED"  # "CONNECTED", "NOT_DETECTED", "TRACKING_LOST"
    calibration_status: CalibrationStatus = CalibrationStatus.NOT_CONFIGURED
    freshness_sec: float = float("inf")
    error_flags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "expected_device_type": self.expected_device_type,
            "detected": self.detected,
            "usb_vendor_id": self.usb_vendor_id,
            "usb_product_id": self.usb_product_id,
            "device_node": self.device_node,
            "driver_package": self.driver_package,
            "tracking_status": self.tracking_status,
            "calibration_status": self.calibration_status.value,
            "freshness_sec": self.freshness_sec,
            "error_flags": list(self.error_flags),
        }


class PikaDiscovery:
    """
    Non-destructive device discovery for AgileX PIKA Sense and Lighthouse base stations.
    Never alters udev rules, never resets USB interfaces, never changes permissions.
    """

    STEAMVR_VID = "28de"
    STEAMVR_PID = "2101"

    @classmethod
    def discover(cls, config_path: Optional[str] = None) -> PikaDeviceReport:
        """
        Passively audits the system for PIKA hardware and returns a structured report.
        """
        report = PikaDeviceReport()

        # 1. Passive USB probe
        cls._probe_usb(report)

        # 2. Check serial device nodes
        cls._probe_serial_nodes(report)

        # 3. Check driver package availability
        cls._probe_driver_packages(report)

        # 4. Audit calibration status without initiating calibration
        cls._audit_calibration(report, config_path=config_path)

        return report

    @classmethod
    def _probe_usb(cls, report: PikaDeviceReport) -> None:
        """Checks for SteamVR wireless dongle (VID 0x28de) via sysfs or lsusb."""
        # Check /sys/bus/usb/devices on Linux if available
        sys_usb = "/sys/bus/usb/devices"
        if os.path.isdir(sys_usb):
            try:
                for dev in os.listdir(sys_usb):
                    dev_path = os.path.join(sys_usb, dev)
                    id_vendor = os.path.join(dev_path, "idVendor")
                    id_product = os.path.join(dev_path, "idProduct")
                    if os.path.isfile(id_vendor) and os.path.isfile(id_product):
                        with open(id_vendor, "r") as f_v, open(id_product, "r") as f_p:
                            v = f_v.read().strip().lower()
                            p = f_p.read().strip().lower()
                            if v == cls.STEAMVR_VID:
                                report.detected = True
                                report.usb_vendor_id = f"0x{v}"
                                report.usb_product_id = f"0x{p}"
                                report.tracking_status = "CONNECTED"
                                return
            except Exception:
                pass

        # Fallback to lsusb command if available
        try:
            res = subprocess.run(["lsusb"], capture_output=True, text=True, timeout=1.5)
            if res.returncode == 0:
                for line in res.stdout.splitlines():
                    if cls.STEAMVR_VID in line.lower() or "valve" in line.lower():
                        report.detected = True
                        report.usb_vendor_id = f"0x{cls.STEAMVR_VID}"
                        report.usb_product_id = f"0x{cls.STEAMVR_PID}"
                        report.tracking_status = "CONNECTED"
                        return
        except Exception:
            pass

        report.detected = False
        report.tracking_status = "NOT_DETECTED"
        report.error_flags.append("SteamVR wireless dongle (0x28de) not detected on USB bus.")

    @classmethod
    def _probe_serial_nodes(cls, report: PikaDeviceReport) -> None:
        """Checks for serial communication nodes non-destructively."""
        for pattern in ["/dev/ttyACM0", "/dev/ttyACM1", "/dev/ttyUSB0", "/dev/ttyUSB50"]:
            if os.path.exists(pattern):
                report.device_node = pattern
                break

    @classmethod
    def _probe_driver_packages(cls, report: PikaDeviceReport) -> None:
        """Checks if vendor packages or Python SDK are importable/present."""
        packages = []
        try:
            import pika_sdk  # noqa: F401
            packages.append("pika_sdk")
        except ImportError:
            pass

        home = os.path.expanduser("~")
        if os.path.isdir(os.path.join(home, "pika_ros")):
            packages.append("~/pika_ros")
        if os.path.isdir(os.path.join(home, "pika_sdk")):
            packages.append("~/pika_sdk")

        report.driver_package = ", ".join(packages) if packages else "None installed"

    @classmethod
    def _audit_calibration(cls, report: PikaDeviceReport, config_path: Optional[str] = None) -> None:
        """Audits calibration artifact without modifying it."""
        path = config_path or os.path.expanduser("~/.config/libsurvive/config.json")

        if not os.path.exists(path):
            report.calibration_status = CalibrationStatus.NOT_CONFIGURED
            report.error_flags.append(f"Calibration file missing: {path}")
            return

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            report.calibration_status = CalibrationStatus.INVALID
            report.error_flags.append(f"Malformed calibration artifact ({path}): {e}")
            return

        # Check for calibrated lighthouses
        lighthouses = data.get("Lighthouses", {})
        if not lighthouses or len(lighthouses) == 0:
            report.calibration_status = CalibrationStatus.NOT_CALIBRATED
            report.error_flags.append("Calibration file exists but contains zero calibrated base stations.")
            return

        # Check file staleness (> 30 days old without refresh)
        try:
            mtime = os.path.getmtime(path)
            age_days = (time.time() - mtime) / 86400.0
            if age_days > 30.0:
                report.calibration_status = CalibrationStatus.STALE
                report.error_flags.append(f"Calibration artifact is {age_days:.1f} days old (recommend recalibration).")
                return
        except Exception:
            pass

        report.calibration_status = CalibrationStatus.CALIBRATED


class TrackingValidator:
    """
    Validates optical 6-DOF tracking packets from PIKA Sense.
    Guarantees that uncalibrated, stale, unnormalized, or NaN values are 100% rejected.
    """

    MAX_TRACKING_AGE_SEC = 0.05  # 50 ms fresh tracking ceiling
    ALLOWED_FRAME_IDS = {"pika_gripper_frame", "base_link", "FLU", "world"}

    @classmethod
    def validate_tracking_data(
        cls,
        pos: List[float],
        quat: List[float],
        frame_id: str = "pika_gripper_frame",
        calibration_status: CalibrationStatus = CalibrationStatus.CALIBRATED,
        tracking_age_sec: float = 0.0,
    ) -> Tuple[bool, List[str]]:
        """
        Validates a 6-DOF spatial pose against strict criteria.
        Returns: (is_valid, errors)
        """
        errors = []

        # 1. Freshness check
        if tracking_age_sec > cls.MAX_TRACKING_AGE_SEC:
            errors.append(f"Tracking packet is stale ({tracking_age_sec*1000:.1f} ms > {cls.MAX_TRACKING_AGE_SEC*1000:.1f} ms limit).")

        # 2. Calibration check
        if calibration_status != CalibrationStatus.CALIBRATED:
            errors.append(f"Optical tracking space is not calibrated (status: {calibration_status.value}).")

        # 3. Coordinate frame check
        if frame_id not in cls.ALLOWED_FRAME_IDS:
            errors.append(f"Unrecognized coordinate frame '{frame_id}' (expected one of {sorted(cls.ALLOWED_FRAME_IDS)}).")

        # 4. Position validation
        if len(pos) != 3:
            errors.append(f"Position vector must have length 3, got {len(pos)}.")
        elif any(math.isnan(x) or math.isinf(x) for x in pos):
            errors.append(f"Position contains NaN or Inf: {pos}.")

        # 5. Quaternion validation
        if len(quat) != 4:
            errors.append(f"Quaternion vector must have length 4, got {len(quat)}.")
        elif any(math.isnan(x) or math.isinf(x) for x in quat):
            errors.append(f"Quaternion contains NaN or Inf: {quat}.")
        else:
            norm = math.sqrt(sum(x * x for x in quat))
            if abs(norm - 1.0) > 0.05:
                errors.append(f"Quaternion is unnormalized (norm: {norm:.4f}, expected ~1.0).")

        # 6. Reject silent identity fallback if uncalibrated
        if pos == [0.0, 0.0, 0.0] and quat == [0.0, 0.0, 0.0, 1.0] and calibration_status != CalibrationStatus.CALIBRATED:
            errors.append("Rejecting uncalibrated identity transform used as fallback.")

        return len(errors) == 0, errors
