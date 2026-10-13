"""
JARVIS-PiPER: Actionable Named Error Hierarchy.
Every error provides:
- What happened
- The most likely cause
- The exact fix command or step
- Reference to the relevant section in USER_MANUAL.md
"""

from typing import Optional


class JarvisError(Exception):
    """Base class for all actionable JARVIS errors."""

    def __init__(
        self,
        message: str,
        cause: str,
        fix: str,
        manual_section: str = "Section 12 (Troubleshooting)",
    ):
        super().__init__(message)
        self.message = message
        self.cause = cause
        self.fix = fix
        self.manual_section = manual_section

    def format_diagnostic(self) -> str:
        return (
            f"\n[JARVIS ERROR] {self.message}\n"
            f"  Possible Cause : {self.cause}\n"
            f"  Recommended Fix: {self.fix}\n"
            f"  Documentation  : Refer to USER_MANUAL.md -> {self.manual_section}\n"
        )


class MotionNotAuthorizedError(JarvisError):
    def __init__(self, details: str = "Physical arm actuation was requested without session authorization."):
        super().__init__(
            message=f"Motion Gate Closed: {details}",
            cause="Session safety interlock requires explicit operator authorization token.",
            fix="Type 'ENABLE MOTION' in the current session or pass --dry-run for non-actuating simulation.",
            manual_section="Section 1 (Safety Warnings & Motion Gate)",
        )


class CanInterfaceDownError(JarvisError):
    def __init__(self, iface: str = "can0"):
        super().__init__(
            message=f"SocketCAN interface '{iface}' is DOWN or absent.",
            cause="USB-to-CAN adapter unplugged, unpowered, or interface not brought up at 1 Mbps.",
            fix=f"sudo ip link set {iface} up type can bitrate 1000000",
            manual_section="Section 3 (Install & CAN Setup)",
        )


class DeviceNotFoundError(JarvisError):
    def __init__(self, device_name: str, identifier: str):
        super().__init__(
            message=f"Required hardware device '{device_name}' ({identifier}) was not detected.",
            cause=f"USB cable disconnected, permission denied, or udev rule missing.",
            fix=f"Check 'lsusb' and verify udev rule; run './install.sh --system' to apply rules.",
            manual_section="Section 2 (What You Need) & Section 4 (First-time Setup)",
        )


class TrackingLostError(JarvisError):
    def __init__(self, age_sec: float):
        super().__init__(
            message=f"PIKA Sense tracking signal lost (stale for {age_sec*1000:.1f} ms).",
            cause="PIKA Sense obscured from base stations, out of FOV, or SteamVR receiver disconnected.",
            fix="Ensure direct line of sight between PIKA Sense and Base Stations; check SteamVR dongle.",
            manual_section="Section 7 (Teleoperation) & Section 12",
        )


class ClutchReleasedError(JarvisError):
    def __init__(self):
        super().__init__(
            message="Operator dead-man clutch button is RELEASED.",
            cause="Clutch button was released or not held during commanded movement.",
            fix="Press and hold the dead-man clutch button (Button 1) on PIKA Sense during movement.",
            manual_section="Section 7 (Teleoperation)",
        )


class EStopTriggeredError(JarvisError):
    def __init__(self, reason: str = "Emergency stop latched."):
        super().__init__(
            message=f"E-Stop Active: {reason}",
            cause="Software emergency stop triggered or physical e-stop open circuit.",
            fix="Resolve hardware condition, clear workspace, and execute 'jarvis reset-estop'.",
            manual_section="Section 1 (Safety Warnings) & Section 12",
        )


class WorkspaceViolationError(JarvisError):
    def __init__(self, pos: list, bounds: dict):
        super().__init__(
            message=f"Target Cartesian position {pos} breaches safety bounding box {bounds}.",
            cause="Commanded end-effector setpoint is outside the verified safe physical workspace.",
            fix="Adjust command setpoint inside workspace box or re-calibrate PIKA workspace origin.",
            manual_section="Section 6 (Calibration) & Section 13 (Hardware Facts)",
        )


class JointLimitViolationError(JarvisError):
    def __init__(self, joint_idx: int, val: float, limits: tuple):
        super().__init__(
            message=f"Joint {joint_idx} target ({val:.3f} rad) exceeds limit [{limits[0]:.3f}, {limits[1]:.3f}].",
            cause="Trajectory generator or policy commanded a configuration past the physical joint stop.",
            fix="Check IK solution and ensure motion trajectory remains within safe envelope.",
            manual_section="Section 13 (Hardware Facts - Joint Limits)",
        )


class VelocityLimitViolationError(JarvisError):
    def __init__(self, max_vel: float, limit: float):
        super().__init__(
            message=f"Commanded velocity ({max_vel:.3f} rad/s) exceeds conservative limit ({limit:.3f} rad/s).",
            cause="Trajectory step size too large or speed scale exceeds safety threshold.",
            fix="Reduce speed scale in config.yaml or interpolate trajectory with smaller time step.",
            manual_section="Section 7 (Teleoperation - Speed Scaling)",
        )


class WatchdogTimeoutError(JarvisError):
    def __init__(self, elapsed_sec: float, timeout_sec: float):
        super().__init__(
            message=f"Command watchdog timed out ({elapsed_sec*1000:.1f} ms > {timeout_sec*1000:.1f} ms limit).",
            cause="Command stream stalled or network/process latency exceeded tolerance. Arm held safely.",
            fix="Inspect sender node publish rate and verify CPU load; restart teleop node cleanly.",
            manual_section="Section 12 (Troubleshooting - Watchdog)",
        )


class CalibrationStaleError(JarvisError):
    def __init__(self, error_m: float, tolerance_m: float = 0.005):
        super().__init__(
            message=f"Calibration error ({error_m:.4f} m) exceeds threshold ({tolerance_m:.4f} m).",
            cause="Base station moved, optical drift occurred, or room infrared lighting changed.",
            fix="Run 'jarvis calibrate' and ensure tracking tag is stationary in FOV.",
            manual_section="Section 6 (Calibration)",
        )


class PermissionDeniedError(JarvisError):
    def __init__(self, path: str, group: str):
        super().__init__(
            message=f"Permission denied accessing '{path}'.",
            cause=f"Current user is not a member of the required group '{group}'.",
            fix=f"sudo usermod -aG {group} $USER  (then log out and back in)",
            manual_section="Section 3 (Install & User Groups)",
        )
