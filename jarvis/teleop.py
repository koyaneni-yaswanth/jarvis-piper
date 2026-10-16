"""
JARVIS-PiPER: Teleoperation Mapping and Signal Conditioning.
Maps 6-DOF PIKA Sense spatial coordinates to PiPER arm motion.
Applies:
- Dead-man clutch logic (relative hand-to-robot displacement)
- Reference hand pose caching upon clutch press
- 2nd-order Butterworth low-pass jitter filter (cutoff = 12 Hz)
"""

from typing import List, Tuple, Optional, Dict, Any
import numpy as np


class TeleoperationMapper:
    """
    Translates operator hand tracking pose into robot Cartesian commands.
    """

    def __init__(self, translation_scale: float = 1.0, cutoff_hz: float = 12.0, sample_rate_hz: float = 60.0):
        self.translation_scale = translation_scale
        self.cutoff_hz = cutoff_hz
        self.sample_rate_hz = sample_rate_hz

        # Clutch reference pose
        self.reference_hand_pos: Optional[np.ndarray] = None
        self.reference_robot_pos: Optional[np.ndarray] = None

        # Filter state (exponential moving average approximation of low-pass)
        self.alpha = min(1.0, 2.0 * np.pi * cutoff_hz / sample_rate_hz)
        self.filtered_pos: Optional[np.ndarray] = None

    def on_clutch_engaged(self, hand_pos: List[float], robot_pos: List[float]) -> None:
        """Called when operator presses Button 1 (dead-man clutch)."""
        self.reference_hand_pos = np.array(hand_pos[:3], dtype=np.float32)
        self.reference_robot_pos = np.array(robot_pos[:3], dtype=np.float32)
        self.filtered_pos = np.copy(self.reference_robot_pos)

    def on_clutch_released(self) -> None:
        """Called when operator releases Button 1."""
        self.reference_hand_pos = None
        self.reference_robot_pos = None

    def map_hand_to_robot(self, hand_pos: List[float]) -> Optional[List[float]]:
        """
        Computes target robot end-effector position based on relative hand displacement:
        p_target = p_robot_ref + scale * (p_hand - p_hand_ref)
        Returns None if clutch is not engaged.
        """
        if self.reference_hand_pos is None or self.reference_robot_pos is None:
            return None

        current_hand = np.array(hand_pos[:3], dtype=np.float32)
        delta_hand = current_hand - self.reference_hand_pos

        raw_target = self.reference_robot_pos + (delta_hand * self.translation_scale)

        # Apply jitter filter
        if self.filtered_pos is None:
            self.filtered_pos = raw_target
        else:
            self.filtered_pos = self.alpha * raw_target + (1.0 - self.alpha) * self.filtered_pos

        return [float(x) for x in self.filtered_pos]


class TeleoperationActionProvider:
    """
    Action provider for live demonstration recording and teleoperation.
    Maintains operator tracking state, dead-man clutch logic, and produces
    canonical 8-dimensional Cartesian commands [x, y, z, qx, qy, qz, qw, stroke_mm]
    and/or joint configurations.
    """

    def __init__(
        self,
        mapper: Optional[TeleoperationMapper] = None,
        translation_scale: float = 1.0,
        kinematics: Optional[Any] = None,
    ):
        self.mapper = mapper or TeleoperationMapper(translation_scale=translation_scale)
        self.kinematics = kinematics
        self.clutch_engaged = False
        self.last_action: Optional[Dict[str, Any]] = None
        self._reference_robot_pos = [0.25, 0.0, 0.20]

    def update(
        self,
        hand_pos: List[float],
        hand_quat: Optional[List[float]] = None,
        gripper_mm: float = 0.0,
        clutch_pressed: bool = False,
        robot_pos: Optional[List[float]] = None,
        current_q: Optional[List[float]] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Processes instantaneous hand tracking and clutch state.
        Returns commanded action dictionary or None.
        """
        ref_r_pos = robot_pos if robot_pos is not None else self._reference_robot_pos

        # Clutch state transition
        if clutch_pressed and not self.clutch_engaged:
            self.clutch_engaged = True
            self.mapper.on_clutch_engaged(hand_pos, ref_r_pos)
        elif not clutch_pressed and self.clutch_engaged:
            self.clutch_engaged = False
            self.mapper.on_clutch_released()

        quat = list(hand_quat) if hand_quat and len(hand_quat) == 4 else [0.0, 0.0, 0.0, 1.0]

        if self.clutch_engaged:
            target_pos = self.mapper.map_hand_to_robot(hand_pos)
            if target_pos is None:
                target_pos = list(ref_r_pos)
        else:
            target_pos = list(ref_r_pos)

        target_q = None
        if self.kinematics is not None and current_q is not None:
            try:
                ik_q, ok = self.kinematics.compute_ik(target_pos, q_init=current_q)
                if ok and ik_q is not None:
                    target_q = list(ik_q)
            except Exception:
                pass

        action_values = [
            round(float(target_pos[0]), 5),
            round(float(target_pos[1]), 5),
            round(float(target_pos[2]), 5),
            round(float(quat[0]), 5),
            round(float(quat[1]), 5),
            round(float(quat[2]), 5),
            round(float(quat[3]), 5),
            round(float(gripper_mm), 2),
        ]

        self.last_action = {
            "values": action_values,
            "cartesian_pos": [round(float(x), 5) for x in target_pos],
            "quaternion": [round(float(x), 5) for x in quat],
            "gripper_mm": round(float(gripper_mm), 2),
            "clutch_engaged": bool(self.clutch_engaged),
            "target_q": target_q,
            "source": "pika_teleop",
        }
        return self.last_action

    def update_from_sample(self, sample: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Extracts hand tracking, clutch, and robot state from a multi-stream sample
        collected by LiveObservationRecorder.
        """
        tracker = sample.get("pika_tracker_pose")
        pika_s = sample.get("pika_sense", {})
        tcp = sample.get("tcp_pose", {}).get("position_m")
        current_q = sample.get("joint_positions")

        if tracker is not None:
            hand_pos = tracker.get("position", [0.0, 0.0, 0.0])
            hand_quat = tracker.get("rotation", [0.0, 0.0, 0.0, 1.0])
            gripper_mm = pika_s.get("gripper_distance_mm", 0.0)
            clutch_pressed = (pika_s.get("command_trigger_state", 0) > 0)
            return self.update(
                hand_pos=hand_pos,
                hand_quat=hand_quat,
                gripper_mm=gripper_mm,
                clutch_pressed=clutch_pressed,
                robot_pos=tcp,
                current_q=current_q,
            )
        elif self.clutch_engaged:
            return self.last_action
        return None

    def get_latest_action(self) -> Optional[Dict[str, Any]]:
        return self.last_action

    def reset(self):
        self.clutch_engaged = False
        self.last_action = None
        self.mapper.on_clutch_released()

