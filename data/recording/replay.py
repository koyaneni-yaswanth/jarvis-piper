"""
Episode Replay & Inspection Tool for JARVIS Datasets.
"""

import os
import json
import time
from typing import Dict, Any, Optional, Iterator


class EpisodeReplayer:
    """
    Loads and streams episode steps for offline evaluation and trajectory visualization.
    """

    def __init__(self, episode_dir: str):
        self.episode_dir = episode_dir
        self.metadata = self._load_json("metadata.json")
        self.trajectory = self._load_json("trajectory.json")

    def _load_json(self, filename: str) -> Dict[str, Any]:
        path = os.path.join(self.episode_dir, filename)
        if not os.path.exists(path):
            raise FileNotFoundError(f"Missing {filename} in {self.episode_dir}")
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def stream_steps(self, playback_speed: float = 1.0) -> Iterator[Dict[str, Any]]:
        """Yields timesteps with optional timing pacing."""
        timesteps = self.trajectory.get("timesteps", [])
        last_t = 0.0

        for s in timesteps:
            t = s.get("timestamp", 0.0)
            if playback_speed > 0 and t > last_t:
                dt = (t - last_t) / playback_speed
                if dt < 0.1:  # cap delay for responsiveness
                    time.sleep(dt)
            last_t = t
            yield s
