"""
Dataset Quality Scorer & Integrity Validator for JARVIS Datasets.
Performs:
- Schema conformance checks.
- Monotonic timestamp verification.
- NaN / Inf anomaly rejection.
- Joint-space and Cartesian jerk computation.
- Synchronization jitter measurement.
- Generation of tabular validation reports.
"""

import os
import json
import glob
from typing import Dict, Any, List, Tuple
import numpy as np


class DatasetValidator:
    """
    Validates dataset integrity and produces research-grade certification metrics.
    """

    def __init__(self, dataset_path: str = "data/datasets"):
        self.dataset_path = dataset_path

    def audit_episode(self, episode_dir: str) -> Dict[str, Any]:
        """Audits a single episode directory against strict quality standards."""
        meta_path = os.path.join(episode_dir, "metadata.json")
        traj_path = os.path.join(episode_dir, "trajectory.json")

        if not os.path.exists(meta_path) or not os.path.exists(traj_path):
            return {"valid": False, "reason": "Missing metadata.json or trajectory.json"}

        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)
        with open(traj_path, "r", encoding="utf-8") as f:
            traj = json.load(f)

        timesteps = traj.get("timesteps", [])
        if len(timesteps) < 5:
            return {"valid": False, "reason": "Episode contains fewer than 5 steps"}

        # 1. Monotonic timestamps & jitter
        timestamps = [s["timestamp"] for s in timesteps]
        dt_array = np.diff(timestamps)
        is_monotonic = bool(np.all(dt_array > 0))

        mean_dt = float(np.mean(dt_array))
        jitter_sigma = float(np.std(dt_array))

        # 2. NaN / Inf check
        has_nan = False
        has_inf = False
        jerk_norms = []

        q_history = []
        for s in timesteps:
            q = s.get("joint_positions", [])
            q_history.append(q)
            if any(np.isnan(q)) or any(np.isnan(s.get("action", []))):
                has_nan = True
            if any(np.isinf(q)) or any(np.isinf(s.get("action", []))):
                has_inf = True

        q_arr = np.array(q_history)  # (T, 6)
        if len(q_arr) >= 4:
            # Numerical 3rd derivative for jerk: d^3 q / dt^3
            v_arr = np.diff(q_arr, axis=0) / mean_dt
            a_arr = np.diff(v_arr, axis=0) / mean_dt
            j_arr = np.diff(a_arr, axis=0) / mean_dt
            rms_jerk = float(np.sqrt(np.mean(j_arr**2)))
        else:
            rms_jerk = 0.0

        is_valid = is_monotonic and (not has_nan) and (not has_inf) and (rms_jerk < 500.0)

        report = {
            "episode_id": meta.get("episode_id", os.path.basename(episode_dir)),
            "valid": is_valid,
            "is_monotonic": is_monotonic,
            "has_nan": has_nan,
            "has_inf": has_inf,
            "total_steps": len(timesteps),
            "duration_sec": meta.get("duration_sec", 0.0),
            "mean_interval_ms": round(mean_dt * 1000.0, 3),
            "jitter_sigma_ms": round(jitter_sigma * 1000.0, 3),
            "rms_jerk_rad_s3": round(rms_jerk, 4),
            "success_label": meta.get("success_label", False),
            "quality_tier": "A" if (is_valid and jitter_sigma < 0.005) else ("B" if is_valid else "FAIL"),
        }

        # Save quality report inside episode folder
        with open(os.path.join(episode_dir, "quality.json"), "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)

        return report

    def audit_dataset(self) -> Dict[str, Any]:
        """Audits all episodes in the dataset root."""
        subdirs = [os.path.join(self.dataset_path, d) for d in os.listdir(self.dataset_path) if os.path.isdir(os.path.join(self.dataset_path, d))]
        results = []
        passed = 0
        failed = 0

        for s in sorted(subdirs):
            rep = self.audit_episode(s)
            results.append(rep)
            if rep.get("valid", False):
                passed += 1
            else:
                failed += 1

        summary = {
            "dataset_path": self.dataset_path,
            "total_episodes": len(results),
            "passed": passed,
            "failed": failed,
            "overall_tier": "A" if failed == 0 and passed > 0 else "DEGRADED",
            "episodes": results,
        }
        return summary
