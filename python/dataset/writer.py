"""
JARVIS-PiPER Episode Writer.
Persists raw multi-modal streams to disk.
"""

import json
import os
import shutil
from typing import Any, Dict, List, Optional
import numpy as np


class EpisodeWriter:
    """Writes an episode trajectory to disk with metadata and streaming journal."""

    def __init__(self, output_dir: str, episode_id: str, metadata: Dict[str, Any]):
        self.episode_dir = os.path.join(output_dir, episode_id)
        self.episode_id = episode_id
        self.metadata = metadata
        self.timesteps: List[Dict[str, Any]] = []

        os.makedirs(self.episode_dir, exist_ok=True)
        os.makedirs(os.path.join(self.episode_dir, "videos"), exist_ok=True)
        os.makedirs(os.path.join(self.episode_dir, "images", "wrist"), exist_ok=True)
        os.makedirs(os.path.join(self.episode_dir, "images", "depth"), exist_ok=True)

        self.journal_path = os.path.join(self.episode_dir, "stream_journal.jsonl")
        self._journal_file = open(self.journal_path, "w", buffering=1, encoding="utf-8")

    def add_step(self, step_data: Dict[str, Any]) -> None:
        self.timesteps.append(step_data)
        self._journal_file.write(json.dumps(step_data) + "\n")

    def finalize(self) -> str:
        self._journal_file.close()
        self.metadata["total_steps"] = len(self.timesteps)

        with open(os.path.join(self.episode_dir, "metadata.json"), "w", encoding="utf-8") as f:
            json.dump(self.metadata, f, indent=2)

        with open(os.path.join(self.episode_dir, "trajectory.json"), "w", encoding="utf-8") as f:
            json.dump({"metadata": self.metadata, "timesteps": self.timesteps}, f, indent=2)

        return self.episode_dir
