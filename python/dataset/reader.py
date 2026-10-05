"""
JARVIS-PiPER Episode Reader.
Loads trajectory, metadata, journals, and video streams from disk.
"""

import json
import os
from typing import Optional
from dataset.episode import Episode


class EpisodeReader:
    """Reads a saved episode directory from disk."""

    def __init__(self, episode_dir: str):
        self.episode_dir = episode_dir
        self.traj_path = os.path.join(episode_dir, "trajectory.json")
        self.meta_path = os.path.join(episode_dir, "metadata.json")
        self._data = self._load()

    def _load(self) -> dict:
        if os.path.exists(self.traj_path):
            with open(self.traj_path, "r", encoding="utf-8") as f:
                return json.load(f)
        elif os.path.exists(self.meta_path):
            with open(self.meta_path, "r", encoding="utf-8") as f:
                return {"metadata": json.load(f), "timesteps": []}
        return {"metadata": {}, "timesteps": []}

    @property
    def metadata(self) -> dict:
        return self._data.get("metadata", {})

    @property
    def timesteps(self) -> list:
        return self._data.get("timesteps", [])

    def to_episode(self) -> Episode:
        meta = self.metadata
        return Episode(
            episode_id=meta.get("episode_id", os.path.basename(self.episode_dir)),
            task_instruction=meta.get("task_instruction", ""),
            metadata=meta,
            timesteps=self.timesteps,
            wrist_video_path=os.path.join(self.episode_dir, "videos", "wrist.mp4"),
            overhead_video_path=os.path.join(self.episode_dir, "videos", "overhead.mp4"),
        )
