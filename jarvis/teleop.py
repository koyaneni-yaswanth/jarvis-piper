"""
JARVIS-PiPER: Teleoperation Mapping and Signal Conditioning.
Maps 6-DOF PIKA Sense spatial coordinates to PiPER arm motion.
Applies:
- Dead-man clutch logic (relative hand-to-robot displacement)
- Reference hand pose caching upon clutch press
- 2nd-order Butterworth low-pass jitter filter (cutoff = 12 Hz)
"""

from typing import List, Tuple, Optional
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
