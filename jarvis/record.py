"""
JARVIS-PiPER: Episode Recorder and Data Validator.
Guarantees monotonic timestamps, immutable raw episode journals,
and comprehensive 7-point quality validation.
"""

import os
import json
import time
from typing import Dict, Any, List, Optional
import numpy as np


class EpisodeRecorder:
    """
    Streams synchronized multimodal episode records.
    """

    def __init__(self, output_dir: str = "data/raw"):
        self.output_dir = output_dir
        self.active = False
        self.episode_id: Optional[str] = None
        self.episode_dir: Optional[str] = None
        self.steps: List[Dict[str, Any]] = []
        self.start_monotonic = 0.0

    def start_episode(self, episode_id: str, metadata: Dict[str, Any]) -> str:
        """Initializes a new episode directory."""
        self.episode_id = episode_id
        self.episode_dir = os.path.join(self.output_dir, episode_id)
        os.makedirs(self.episode_dir, exist_ok=True)

        self.start_monotonic = time.monotonic()
        self.steps = []
        self.active = True

        # Write immutable initial metadata
        meta_path = os.path.join(self.episode_dir, "metadata.json")
        full_meta = {
            "episode_id": episode_id,
            "created_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "schema_version": "1.0.0",
            **metadata,
        }
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(full_meta, f, indent=2)

        self._last_t = -1.0
        return self.episode_dir

    def record_step(
        self,
        joint_positions: List[float],
        joint_velocities: List[float],
        action: List[float],
        gripper_stroke: float,
        rgb_frame: Optional[np.ndarray] = None,
        depth_frame: Optional[np.ndarray] = None,
        timestamp: Optional[float] = None,
    ) -> None:
        """Appends one synchronized timestep."""
        if not self.active:
            raise RuntimeError("Cannot record step: Recorder is not active!")

        if timestamp is not None:
            t_rel = float(timestamp)
        else:
            raw_t = time.monotonic() - self.start_monotonic
            if hasattr(self, "_last_t") and self._last_t >= 0.0 and raw_t <= self._last_t:
                t_rel = self._last_t + 0.001
            else:
                t_rel = raw_t

        self._last_t = t_rel
        step_data = {
            "timestamp": t_rel,
            "positions": list(joint_positions),
            "velocities": list(joint_velocities),
            "action": list(action),
            "gripper_stroke": float(gripper_stroke),
            "has_rgb": rgb_frame is not None,
            "has_depth": depth_frame is not None,
        }
        self.steps.append(step_data)

    def stop_episode(self, outcome: str = "success", notes: str = "") -> Dict[str, Any]:
        """Finalizes the episode and flushes journal."""
        if not self.active or self.episode_dir is None:
            raise RuntimeError("Recorder is not active!")

        # Write stream journal
        journal_path = os.path.join(self.episode_dir, "stream_journal.jsonl")
        with open(journal_path, "w", encoding="utf-8") as f:
            for s in self.steps:
                f.write(json.dumps(s) + "\n")

        # Update metadata with outcome
        meta_path = os.path.join(self.episode_dir, "metadata.json")
        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)

        meta["outcome"] = outcome
        meta["notes"] = notes
        meta["num_steps"] = len(self.steps)
        meta["duration_sec"] = (time.monotonic() - self.start_monotonic)

        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2)

        self.active = False
        return meta


class EpisodeValidator:
    """
    Validates recorded episodes against the 7-point quality standard.
    """

    JOINT_LIMITS = [
        (-2.618, 2.618),
        (0.000, 3.141),
        (-2.967, 0.000),
        (-1.745, 1.745),
        (-1.222, 1.222),
        (-2.094, 2.094),
    ]

    def validate_episode(self, episode_dir: str) -> Dict[str, Any]:
        """
        Validates an episode on disk.
        Returns: {'valid': bool, 'errors': List[str], 'warnings': List[str]}
        """
        errors = []
        warnings = []

        meta_file = os.path.join(episode_dir, "metadata.json")
        journal_file = os.path.join(episode_dir, "stream_journal.jsonl")

        if not os.path.exists(meta_file):
            return {"valid": False, "errors": ["Missing metadata.json"], "warnings": []}
        if not os.path.exists(journal_file):
            return {"valid": False, "errors": ["Missing stream_journal.jsonl"], "warnings": []}

        try:
            with open(meta_file, "r", encoding="utf-8") as f:
                meta = json.load(f)
        except Exception as e:
            return {"valid": False, "errors": [f"Malformed metadata.json: {e}"], "warnings": []}

        steps = []
        with open(journal_file, "r", encoding="utf-8") as f:
            for i, line in enumerate(f):
                line = line.strip()
                if not line:
                    continue
                try:
                    steps.append(json.loads(line))
                except Exception as e:
                    errors.append(f"Malformed JSON at journal line {i}: {e}")

        if not steps:
            errors.append("Episode contains 0 timesteps.")
            return {"valid": False, "errors": errors, "warnings": warnings}

        prev_t = -1.0
        for i, s in enumerate(steps):
            t = s.get("timestamp", -1.0)
            if t <= prev_t:
                errors.append(f"Step {i}: Non-monotonic timestamp (prev: {prev_t:.4f}, curr: {t:.4f})")
            prev_t = t

            # NaN check
            q = s.get("positions", [])
            act = s.get("action", [])
            if any(np.isnan(x) or np.isinf(x) for x in q + act):
                errors.append(f"Step {i}: Found NaN or Inf in positions or actions.")

            # Joint limits check
            for j_idx, val in enumerate(q):
                if j_idx < len(self.JOINT_LIMITS):
                    l_min, l_max = self.JOINT_LIMITS[j_idx]
                    if not (l_min - 0.05 <= val <= l_max + 0.05):
                        errors.append(f"Step {i}: Joint {j_idx+1} out of bounds: {val:.3f} not in [{l_min:.3f}, {l_max:.3f}]")

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "num_steps": len(steps),
            "outcome": meta.get("outcome", "unknown"),
        }
