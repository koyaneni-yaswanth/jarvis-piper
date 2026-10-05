"""
JARVIS-PiPER Manipulation Phase Segmenter.
"""

from typing import Any, Dict, List


class PhaseSegmenter:
    """Decomposes demonstration trajectories into semantic sub-task phases."""

    def segment(self, timesteps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        T = len(timesteps)
        for i, s in enumerate(timesteps):
            stroke = s.get("gripper_stroke", 0.035)
            if i < T * 0.3:
                phase = "APPROACH"
            elif stroke < 0.015:
                phase = "GRASP"
            elif i < T * 0.8:
                phase = "TRANSPORT"
            else:
                phase = "RETRACT"
            s["semantic_phase"] = phase
        return timesteps
