"""
Dataset and System Performance Benchmark Suite.
"""

import json
from pathlib import Path
from typing import Dict, List, Any
import numpy as np

from .metrics import compute_trajectory_jerk, compute_sync_jitter, compute_gripper_efficiency


class DatasetBenchmark:
    """
    Evaluates dataset episodes against quality benchmarks.
    """

    def __init__(self, raw_dir: str = "dataset/raw"):
        self.raw_dir = Path(raw_dir)

    def evaluate(self) -> Dict[str, Any]:
        """Scans all episodes and aggregates benchmark statistics."""
        episodes = [p for p in self.raw_dir.iterdir() if p.is_dir() and (p / "metadata.json").exists()]
        if not episodes:
            return {"error": "No episodes found", "total_episodes": 0}

        all_jerks = []
        all_jitters = []
        all_drop_ratios = []

        for ep in episodes:
            traj_file = ep / "trajectory.json"
            if not traj_file.exists():
                continue
            with open(traj_file, "r") as f:
                data = json.load(f)

            # Timestamps & jitter
            ts = data.get("timestamps", [])
            if len(ts) > 1:
                j_info = compute_sync_jitter(ts)
                all_jitters.append(j_info["jitter_std_ms"])
                all_drop_ratios.append(j_info["drop_ratio"])

            # Jerk
            joints = np.array(data.get("joint_positions", []))
            if len(joints) > 5:
                all_jerks.append(compute_trajectory_jerk(joints))

        return {
            "total_episodes": len(episodes),
            "mean_jerk": float(np.mean(all_jerks)) if all_jerks else 0.0,
            "mean_jitter_ms": float(np.mean(all_jitters)) if all_jitters else 0.0,
            "mean_drop_ratio": float(np.mean(all_drop_ratios)) if all_drop_ratios else 0.0,
            "quality_grade": "A" if (all_drop_ratios and np.mean(all_drop_ratios) < 0.01) else "B",
        }
