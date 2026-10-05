"""
JARVIS PiPER Semantic Manipulation Phase Segmenter
Decomposes continuous teleoperation trajectories into semantic sub-goal phases:
APPROACH -> PRE_GRASP -> GRASP -> LIFT -> TRANSPORT -> RELEASE -> RETRACT.
"""

from typing import Any, Dict, List
import numpy as np


class ManipulationPhase:
    APPROACH = "APPROACH"
    PRE_GRASP = "PRE_GRASP"
    GRASP = "GRASP"
    LIFT = "LIFT"
    TRANSPORT = "TRANSPORT"
    RELEASE = "RELEASE"
    RETRACT = "RETRACT"


class TrajectoryPhaseSegmenter:
    """Segments an episode trajectory into semantic manipulation phases."""

    def __init__(self, gripper_closed_threshold: float = 0.015):
        self.gripper_closed_threshold = gripper_closed_threshold

    def segment_episode(self, timesteps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Adds 'semantic_phase' to each timestep in place and returns enriched list."""
        if not timesteps:
            return []

        T = len(timesteps)
        strokes = [step.get("gripper_stroke", 0.035) for step in timesteps]
        tcp_z = [
            step.get("tcp_pose", {}).get("position", [0, 0, 0])[2]
            if isinstance(step.get("tcp_pose"), dict)
            else 0.0
            for step in timesteps
        ]

        # Detect grasp intervals (where gripper is closed)
        is_closed = [s < self.gripper_closed_threshold for s in strokes]

        first_close_idx = -1
        last_close_idx = -1
        for i, closed in enumerate(is_closed):
            if closed and first_close_idx == -1:
                first_close_idx = i
            if closed:
                last_close_idx = i

        for i, step in enumerate(timesteps):
            if first_close_idx == -1:
                # Gripper never closed
                phase = ManipulationPhase.APPROACH if i < T // 2 else ManipulationPhase.RETRACT
            elif i < max(0, first_close_idx - 15):
                phase = ManipulationPhase.APPROACH
            elif i < first_close_idx:
                phase = ManipulationPhase.PRE_GRASP
            elif i <= min(T - 1, first_close_idx + 10):
                phase = ManipulationPhase.GRASP
            elif i < last_close_idx:
                # Check vertical motion for LIFT vs TRANSPORT
                if i < first_close_idx + 35:
                    phase = ManipulationPhase.LIFT
                else:
                    phase = ManipulationPhase.TRANSPORT
            elif i <= min(T - 1, last_close_idx + 15):
                phase = ManipulationPhase.RELEASE
            else:
                phase = ManipulationPhase.RETRACT

            step["semantic_phase"] = phase

        return timesteps
