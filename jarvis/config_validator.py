"""
JARVIS-PiPER: Configuration Validator.
Performs strict schema and safety boundary validation on config.yaml.
Ensures no dangerous speeds, illegal CAN bitrates, or unbounded workspace boxes
can be loaded by the robot controllers.
"""

import os
import yaml
from typing import Dict, Any, List, Tuple


class ConfigValidator:
    """
    Validates JARVIS configuration files against physical robot specifications
    and safety envelope constraints.
    """

    ALLOWED_BITRATES = [1000000]  # PiPER requires 1 Mbps
    MAX_SPEED_SCALE = 0.20        # Conservative 20% limit for safe supervised operation
    MAX_VELOCITY_RAD_S = 2.00     # Hard velocity ceiling
    MAX_WATCHDOG_SEC = 0.20       # 200 ms maximum watchdog tolerance
    MAX_TRACKING_AGE_SEC = 0.10   # 100 ms maximum tracking latency

    @classmethod
    def validate_file(cls, path: str = "config.yaml") -> Dict[str, Any]:
        """Validates configuration file at path and returns status report."""
        if not os.path.exists(path):
            return {
                "valid": False,
                "errors": [f"Configuration file not found: {path}"],
                "warnings": [],
                "config": {},
            }

        try:
            with open(path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
        except Exception as e:
            return {
                "valid": False,
                "errors": [f"Failed to parse YAML in {path}: {e}"],
                "warnings": [],
                "config": {},
            }

        return cls.validate_dict(config)

    @classmethod
    def validate_dict(cls, config: Dict[str, Any]) -> Dict[str, Any]:
        """Validates configuration dictionary against safety rules."""
        errors: List[str] = []
        warnings: List[str] = []

        if not isinstance(config, dict):
            return {"valid": False, "errors": ["Root configuration must be a mapping/dict"], "warnings": [], "config": {}}

        # 1. Schema version
        if "schema_version" not in config:
            warnings.append("Missing 'schema_version' (defaulting to 1.0.0)")

        # 2. Robot section
        robot = config.get("robot", {})
        if not isinstance(robot, dict):
            errors.append("'robot' section must be a dictionary")
        else:
            bitrate = robot.get("bitrate", 1000000)
            if bitrate not in cls.ALLOWED_BITRATES:
                errors.append(
                    f"Invalid robot bitrate: {bitrate} bps. PiPER requires exactly 1,000,000 bps (1 Mbps)."
                )

            freq = robot.get("control_frequency_hz", 60.0)
            if not (10.0 <= freq <= 200.0):
                warnings.append(f"Unusual control frequency: {freq} Hz (expected 20-100 Hz)")

        # 3. Safety section
        safety = config.get("safety", {})
        if not isinstance(safety, dict):
            errors.append("'safety' section must be a dictionary")
        else:
            speed_scale = safety.get("speed_scale", 0.10)
            if speed_scale > cls.MAX_SPEED_SCALE:
                errors.append(
                    f"Safety speed_scale {speed_scale:.2f} exceeds conservative ceiling {cls.MAX_SPEED_SCALE:.2f}."
                )

            max_vel = safety.get("max_joint_velocity_rad_s", 1.50)
            if max_vel > cls.MAX_VELOCITY_RAD_S:
                errors.append(
                    f"max_joint_velocity_rad_s {max_vel:.2f} exceeds physical safety ceiling {cls.MAX_VELOCITY_RAD_S:.2f}."
                )

            watchdog = safety.get("watchdog_timeout_sec", 0.10)
            if watchdog > cls.MAX_WATCHDOG_SEC:
                warnings.append(
                    f"watchdog_timeout_sec ({watchdog:.2f}s) is above recommended 0.10s."
                )

            tracking = safety.get("tracking_timeout_sec", 0.05)
            if tracking > cls.MAX_TRACKING_AGE_SEC:
                warnings.append(
                    f"tracking_timeout_sec ({tracking:.2f}s) is above recommended 0.05s."
                )

            # Workspace bounds
            box = safety.get("workspace_box", {})
            if isinstance(box, dict):
                for axis in ["x", "y", "z"]:
                    limits = box.get(axis)
                    if not (isinstance(limits, (list, tuple)) and len(limits) == 2 and limits[0] < limits[1]):
                        errors.append(f"Invalid workspace_box bounds for axis '{axis}': {limits}")
            else:
                errors.append("'workspace_box' in safety section must be a dictionary with x, y, z")

        # 4. Teleop section
        teleop = config.get("teleop", {})
        if isinstance(teleop, dict):
            scale = teleop.get("translation_scale", 1.0)
            if not (0.1 <= scale <= 2.0):
                warnings.append(f"teleop.translation_scale ({scale}) is outside recommended range [0.1, 2.0]")

        is_valid = len(errors) == 0
        return {
            "valid": is_valid,
            "errors": errors,
            "warnings": warnings,
            "config": config,
        }
