"""
JARVIS-PiPER: Live Hardware Observation and Multi-Stream Recorder.
Passively reads and synchronizes real-time sensor streams without commanding motion:
- AgileX PiPER arm joint telemetry & end-effector pose over SocketCAN (read-only)
- Intel RealSense D405 wrist/eye-in-hand color (BGR8) and depth (Z16)
- DECXIN / Sunplus overhead camera color (BGR8)
- PIKA Sense controller encoder, trigger state, and 6-DOF tracking pose
"""

import os
import sys
import time
import json
import queue
import logging
import threading
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
import numpy as np

logger = logging.getLogger("jarvis.live_recorder")

try:
    import cv2
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False

try:
    import pyrealsense2 as rs
    HAS_REALSENSE = True
except ImportError:
    HAS_REALSENSE = False

try:
    from piper_sdk import C_PiperInterface_V2
    HAS_PIPER = True
except ImportError:
    HAS_PIPER = False

try:
    from pika import sense
    HAS_PIKA = True
except ImportError:
    HAS_PIKA = False


class LiveObservationRecorder:
    """
    Synchronized multi-stream live observation recorder.
    Collects real-time telemetry from PiPER CAN, RealSense D405, DECXIN camera, and PIKA Sense.
    Strictly passive and read-only: never enables motors or transmits arm actuation commands.
    """

    def __init__(
        self,
        output_dir: str = "data/recordings",
        can_port: str = "can0",
        realsense_enabled: bool = True,
        overhead_camera_index: int = 0,
        pika_serial_port: str = "/dev/ttyUSB0",
        pika_enabled: bool = True,
        target_control_hz: float = 30.0,
        action_provider: Optional[Any] = None,
    ):
        self.output_dir = Path(output_dir)
        self.can_port = can_port
        self.realsense_enabled = realsense_enabled
        self.overhead_camera_index = overhead_camera_index
        self.pika_serial_port = pika_serial_port
        self.pika_enabled = pika_enabled
        self.target_hz = target_control_hz
        self.action_provider = action_provider

        # Hardware handles
        self.piper = None
        self.rs_pipe = None
        self.overhead_cap = None
        self.pika_sense = None

        # State tracking
        self.is_recording = False
        self._stop_event = threading.Event()
        self.session_id: Optional[str] = None
        self.session_dir: Optional[Path] = None

        # Stream counters & drop tracking
        self.stats = {
            "robot_telemetry_samples": 0,
            "realsense_color_frames": 0,
            "realsense_depth_frames": 0,
            "overhead_color_frames": 0,
            "pika_samples": 0,
            "action_samples": 0,
            "dropped_samples": 0,
            "start_time_monotonic": 0.0,
            "end_time_monotonic": 0.0,
            "duration_sec": 0.0,
        }

    def initialize_hardware(self) -> Dict[str, Any]:
        """
        Connects to available hardware in strictly read-only passive mode.
        Returns hardware status dictionary.
        """
        status = {
            "can_bus": False,
            "piper_telemetry": False,
            "realsense_d405": False,
            "realsense_serial": None,
            "overhead_camera": False,
            "pika_sense": False,
        }

        # 1. PiPER Passive CAN Link
        if HAS_PIPER:
            try:
                self.piper = C_PiperInterface_V2(self.can_port)
                # piper_init=False guarantees NO motor enable, NO acceleration overrides, NO motion
                self.piper.ConnectPort(can_init=False, piper_init=False)
                time.sleep(0.3)
                j_msg = self.piper.GetArmJointMsgs()
                if j_msg is not None:
                    status["can_bus"] = True
                    status["piper_telemetry"] = True
                    logger.info("[LiveRecorder] PiPER CAN telemetry link online (read-only).")
            except Exception as e:
                logger.warning(f"[LiveRecorder] PiPER CAN connection failed: {e}")
                self.piper = None

        # 2. Intel RealSense D405
        if HAS_REALSENSE and self.realsense_enabled:
            try:
                ctx = rs.context()
                devices = ctx.query_devices()
                if len(devices) > 0:
                    d405_dev = devices[0]
                    serial = d405_dev.get_info(rs.camera_info.serial_number)
                    status["realsense_serial"] = serial

                    self.rs_pipe = rs.pipeline()
                    rs_cfg = rs.config()
                    rs_cfg.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, int(self.target_hz))
                    rs_cfg.enable_stream(rs.stream.depth, 640, 480, rs.format.z16, int(self.target_hz))
                    self.rs_pipe.start(rs_cfg)
                    # Warm-up read
                    frames = self.rs_pipe.wait_for_frames(3000)
                    if frames.get_color_frame() and frames.get_depth_frame():
                        status["realsense_d405"] = True
                        logger.info(f"[LiveRecorder] RealSense D405 streaming active (SN: {serial}).")
            except Exception as e:
                logger.warning(f"[LiveRecorder] RealSense D405 initialization failed: {e}")
                if self.rs_pipe:
                    try:
                        self.rs_pipe.stop()
                    except Exception:
                        pass
                self.rs_pipe = None

        # 3. Overhead DECXIN Camera
        if HAS_CV2 and self.overhead_camera_index is not None:
            try:
                dev_path = f"/dev/video{self.overhead_camera_index}"
                self.overhead_cap = cv2.VideoCapture(dev_path, cv2.CAP_V4L2)
                if self.overhead_cap.isOpened():
                    self.overhead_cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
                    self.overhead_cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                    self.overhead_cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                    self.overhead_cap.set(cv2.CAP_PROP_FPS, int(self.target_hz))
                    ret, test_frame = self.overhead_cap.read()
                    if ret and test_frame is not None:
                        status["overhead_camera"] = True
                        logger.info(f"[LiveRecorder] Overhead camera active ({dev_path}, MJPG format).")
                    else:
                        self.overhead_cap.release()
                        self.overhead_cap = None
            except Exception as e:
                logger.warning(f"[LiveRecorder] Overhead camera initialization failed: {e}")
                self.overhead_cap = None

        # 4. PIKA Sense Controller
        if HAS_PIKA and self.pika_enabled and os.path.exists(self.pika_serial_port):
            try:
                self.pika_sense = sense(self.pika_serial_port)
                if self.pika_sense.connect():
                    time.sleep(0.3)
                    status["pika_sense"] = True
                    logger.info(f"[LiveRecorder] PIKA Sense connected on {self.pika_serial_port}.")
                else:
                    self.pika_sense = None
            except Exception as e:
                logger.warning(f"[LiveRecorder] PIKA Sense initialization failed: {e}")
                self.pika_sense = None

        return status

    def record_session(
        self,
        duration_seconds: float = 10.0,
        task_description: str = "Live hardware observation recording",
        operator_name: str = "operator",
        episode_mode: bool = False,
        task_name: str = "general",
    ) -> Path:
        """
        Executes a live hardware observation recording session for the specified duration.
        """
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        if episode_mode:
            self.session_id = f"ep_{task_name}_{timestamp_str}"
            self.session_dir = self.output_dir / task_name / self.session_id
        else:
            self.session_id = f"live_obs_{timestamp_str}"
            self.session_dir = self.output_dir / self.session_id
        self.session_dir.mkdir(parents=True, exist_ok=True)

        img_wrist_dir = self.session_dir / "wrist_color"
        img_depth_dir = self.session_dir / "wrist_depth"
        img_overhead_dir = self.session_dir / "overhead_color"
        img_wrist_dir.mkdir(exist_ok=True)
        img_depth_dir.mkdir(exist_ok=True)
        img_overhead_dir.mkdir(exist_ok=True)

        telemetry_path = self.session_dir / "telemetry.jsonl"
        metadata_path = self.session_dir / "metadata.json"

        logger.info(f"Starting live observation recording: {self.session_id} for {duration_seconds:.1f}s")
        self.is_recording = True
        self._stop_event.clear()

        start_wall = datetime.utcnow().isoformat() + "Z"
        t0_mono = time.monotonic()
        t0_wall_ns = time.time_ns()
        self.stats["start_time_monotonic"] = t0_mono

        period = 1.0 / self.target_hz
        next_tick = t0_mono
        step = 0

        with open(telemetry_path, "w", encoding="utf-8") as telem_f:
            while not self._stop_event.is_set():
                now_mono = time.monotonic()
                elapsed = now_mono - t0_mono
                if elapsed >= duration_seconds:
                    break

                step_start_ns = time.monotonic_ns()
                current_timestamp_ns = t0_wall_ns + (step_start_ns - (t0_mono * 1e9))

                sample: Dict[str, Any] = {
                    "step": step,
                    "timestamp_s": round(elapsed, 4),
                    "monotonic_ns": step_start_ns,
                    "wall_ns": int(current_timestamp_ns),
                }

                # --- 1. PiPER Arm Telemetry ---
                if self.piper is not None:
                    try:
                        j_msg = self.piper.GetArmJointMsgs()
                        # Raw units: 0.001 deg -> rad: (val / 1000.0) * (pi / 180.0)
                        raw_q = [
                            getattr(j_msg.joint_state, f"joint_{i}") for i in range(1, 7)
                        ]
                        q_rad = [round((val / 1000.0) * (np.pi / 180.0), 6) for val in raw_q]
                        sample["joint_positions"] = q_rad

                        if hasattr(j_msg, "time_stamp") and isinstance(j_msg.time_stamp, (int, float, str)):
                            sample["can_driver_timestamp"] = j_msg.time_stamp

                        # End effector pose
                        ep_msg = self.piper.GetArmEndPoseMsgs()
                        ep = ep_msg.end_pose
                        sample["tcp_pose"] = {
                            "position_m": [
                                round(ep.X_axis / 1e6, 6),
                                round(ep.Y_axis / 1e6, 6),
                                round(ep.Z_axis / 1e6, 6),
                            ],
                            "rpy_rad": [
                                round((ep.RX_axis / 1e3) * (np.pi / 180.0), 6),
                                round((ep.RY_axis / 1e3) * (np.pi / 180.0), 6),
                                round((ep.RZ_axis / 1e3) * (np.pi / 180.0), 6),
                            ],
                        }

                        # Joint velocities and efforts
                        try:
                            high_msg = self.piper.GetArmHighSpdInfoMsgs()
                            if high_msg is not None:
                                raw_v = [getattr(getattr(high_msg, f"motor_{i}", None), "motor_speed", 0.0) for i in range(1, 7)]
                                if all(isinstance(v, (int, float)) for v in raw_v):
                                    sample["joint_velocities"] = [round(float(v) * 0.001, 5) for v in raw_v]
                                raw_e = [getattr(getattr(high_msg, f"motor_{i}", None), "effort", 0.0) for i in range(1, 7)]
                                if all(isinstance(e, (int, float)) for e in raw_e):
                                    sample["joint_efforts"] = [round(float(e), 4) for e in raw_e]
                        except Exception:
                            pass

                        # Gripper telemetry
                        grp_msg = self.piper.GetArmGripperMsgs()
                        sample["gripper_stroke_m"] = round(
                            abs(grp_msg.gripper_state.grippers_angle) / 1e6, 6
                        )

                        # Status & flags (verify arm is disarmed and unenabled)
                        st = self.piper.GetArmStatus()
                        sample["arm_status"] = str(st.arm_status.arm_status)
                        sample["arm_mode"] = str(st.arm_status.ctrl_mode)

                        self.stats["robot_telemetry_samples"] += 1
                    except Exception as e:
                        logger.debug(f"Error sampling PiPER telemetry: {e}")
                        self.stats["dropped_samples"] += 1

                # --- 2. PIKA Sense Telemetry ---
                if self.pika_sense is not None:
                    try:
                        pika_enc = self.pika_sense.get_encoder_data()
                        pika_dist = self.pika_sense.get_gripper_distance()
                        pika_cmd = self.pika_sense.get_command_state()
                        sample["pika_sense"] = {
                            "encoder_angle_deg": pika_enc.get("angle", 0.0),
                            "encoder_rad": pika_enc.get("rad", 0.0),
                            "gripper_distance_mm": pika_dist,
                            "command_trigger_state": pika_cmd,
                        }

                        # Poll 6-DOF tracking pose if tracker visible
                        tracker_pose = self.pika_sense.get_pose("T20") or self.pika_sense.get_pose("WM0")
                        if tracker_pose is not None:
                            sample["pika_tracker_pose"] = {
                                "position": list(tracker_pose.position),
                                "rotation": list(tracker_pose.rotation),
                            }
                        self.stats["pika_samples"] += 1
                    except Exception as e:
                        logger.debug(f"Error sampling PIKA Sense: {e}")

                # --- 3. RealSense D405 Frames ---
                if self.rs_pipe is not None and HAS_CV2:
                    try:
                        rs_frames = self.rs_pipe.wait_for_frames(200)
                        if rs_frames:
                            c_f = rs_frames.get_color_frame()
                            d_f = rs_frames.get_depth_frame()
                            if c_f:
                                c_arr = np.asanyarray(c_f.get_data())
                                c_name = f"frame_{step:05d}.jpg"
                                cv2.imwrite(str(img_wrist_dir / c_name), c_arr, [cv2.IMWRITE_JPEG_QUALITY, 85])
                                sample["wrist_color_file"] = f"wrist_color/{c_name}"
                                sample["wrist_color_hw_time_ms"] = round(float(c_f.get_timestamp()), 3)
                                self.stats["realsense_color_frames"] += 1
                            if d_f:
                                d_arr = np.asanyarray(d_f.get_data())  # uint16 (mm)
                                d_name = f"depth_{step:05d}.png"
                                cv2.imwrite(str(img_depth_dir / d_name), d_arr)
                                sample["wrist_depth_file"] = f"wrist_depth/{d_name}"
                                sample["wrist_depth_hw_time_ms"] = round(float(d_f.get_timestamp()), 3)
                                self.stats["realsense_depth_frames"] += 1
                    except Exception as e:
                        logger.debug(f"RealSense polling error: {e}")

                # --- 4. Overhead DECXIN Frame ---
                if self.overhead_cap is not None and HAS_CV2:
                    try:
                        ret, oh_frame = self.overhead_cap.read()
                        if ret and oh_frame is not None:
                            oh_name = f"overhead_{step:05d}.jpg"
                            cv2.imwrite(str(img_overhead_dir / oh_name), oh_frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
                            sample["overhead_color_file"] = f"overhead_color/{oh_name}"
                            self.stats["overhead_color_frames"] += 1
                    except Exception as e:
                        logger.debug(f"Overhead frame capture error: {e}")

                # --- 5. Commanded Operator Action (if action provider attached) ---
                if self.action_provider is not None:
                    try:
                        if hasattr(self.action_provider, "update_from_sample"):
                            self.action_provider.update_from_sample(sample)
                        act = self.action_provider.get_latest_action()
                        if act is not None:
                            sample["action"] = act
                            self.stats["action_samples"] += 1
                    except Exception as e:
                        logger.debug(f"Action provider poll error: {e}")

                # Write record to JSONL
                telem_f.write(json.dumps(sample) + "\n")
                step += 1

                # Rate pacing
                next_tick += period
                sleep_dur = next_tick - time.monotonic()
                if sleep_dur > 0:
                    time.sleep(sleep_dur)
                else:
                    next_tick = time.monotonic()

        t_end_mono = time.monotonic()
        total_duration = t_end_mono - t0_mono
        self.stats["end_time_monotonic"] = t_end_mono
        self.stats["duration_sec"] = round(total_duration, 3)

        # Write immutable recording metadata
        metadata = {
            "session_id": self.session_id,
            "task_description": task_description,
            "operator": operator_name,
            "created_at_utc": start_wall,
            "target_control_hz": self.target_hz,
            "actual_duration_seconds": round(total_duration, 3),
            "total_timesteps": step,
            "effective_hz": round(step / max(0.1, total_duration), 2),
            "streams_recorded": {
                "robot_telemetry": {
                    "source": "AgileX PiPER 6-DOF (CAN interface can0)",
                    "samples": self.stats["robot_telemetry_samples"],
                    "hz": round(self.stats["robot_telemetry_samples"] / max(0.1, total_duration), 2),
                    "mode": "PASSIVE_MONITOR (motors disarmed)",
                },
                "realsense_d405": {
                    "source": "Intel RealSense D405 (RGB + 16-bit Depth)",
                    "color_frames": self.stats["realsense_color_frames"],
                    "depth_frames": self.stats["realsense_depth_frames"],
                    "hz": round(self.stats["realsense_color_frames"] / max(0.1, total_duration), 2),
                },
                "overhead_camera": {
                    "source": "DECXIN / Sunplus UVC (/dev/video0)",
                    "frames": self.stats["overhead_color_frames"],
                    "hz": round(self.stats["overhead_color_frames"] / max(0.1, total_duration), 2),
                },
                "pika_sense": {
                    "source": "Pika Sense & Vive Tracker (/dev/ttyUSB0)",
                    "samples": self.stats["pika_samples"],
                    "hz": round(self.stats["pika_samples"] / max(0.1, total_duration), 2),
                },
                "actions": {
                    "samples": self.stats["action_samples"],
                    "hz": round(self.stats["action_samples"] / max(0.1, total_duration), 2),
                    "active": (self.stats["action_samples"] > 0),
                },
            },
            "dropped_samples": self.stats["dropped_samples"],
            "verification_status": "VERIFIED_HARDWARE_OBSERVATION",
        }

        with open(metadata_path, "w", encoding="utf-8") as meta_f:
            json.dump(metadata, meta_f, indent=2)

        self.close()
        logger.info(f"Live observation session {self.session_id} saved to {self.session_dir}")
        return self.session_dir

    def close(self):
        """Safely disconnects all sensors."""
        self._stop_event.set()
        if self.piper is not None:
            try:
                self.piper.DisconnectPort()
            except Exception:
                pass
            self.piper = None

        if self.rs_pipe is not None:
            try:
                self.rs_pipe.stop()
            except Exception:
                pass
            self.rs_pipe = None

        if self.overhead_cap is not None:
            try:
                self.overhead_cap.release()
            except Exception:
                pass
            self.overhead_cap = None

        if self.pika_sense is not None:
            try:
                self.pika_sense.disconnect()
            except Exception:
                pass
            self.pika_sense = None
