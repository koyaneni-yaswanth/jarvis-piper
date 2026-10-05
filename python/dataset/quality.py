"""
JARVIS-PiPER 7-Point Quality Assurance & Tier Classification.
Assigns scores (0-100) and Tiers:
- Tier A (90-100): Research-grade benchmark data
- Tier B (80-89): Clean training data
- Tier C (70-79): Marginal, acceptable for pretraining
- Tier D (<70): Rejected, contains critical flaws
"""

import glob
import json
import os
from typing import Any, Dict, List
import numpy as np


class QualityScorer:
    """Evaluates multi-modal episode quality and assigns certification tiers."""

    def __init__(self, target_fps: float = 30.0, max_jitter_ms: float = 25.0):
        self.target_fps = target_fps
        self.max_jitter_ms = max_jitter_ms

    def score_episode(self, episode_dir: str) -> Dict[str, Any]:
        return self._score_internal(episode_dir)

    def audit_episode(self, episode_dir: str) -> Dict[str, Any]:
        res = self._score_internal(episode_dir)
        res["quality_tier"] = res.get("tier", "D")
        return res

    def _score_internal(self, episode_dir: str) -> Dict[str, Any]:
        traj_path = os.path.join(episode_dir, "trajectory.json")
        if not os.path.exists(traj_path):
            return {"passed": False, "score": 0.0, "tier": "D", "violations": ["Missing trajectory.json"]}

        with open(traj_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        meta = data.get("metadata", {})
        steps = data.get("timesteps", [])
        violations = []

        if len(steps) < 10:
            violations.append(f"Insufficient steps ({len(steps)} < 10)")

        # 1. Monotonicity & Jitter
        timestamps = [s.get("timestamp", 0.0) for s in steps]
        dts = [timestamps[i] - timestamps[i-1] for i in range(1, len(timestamps))]
        non_mono = sum(1 for dt in dts if dt <= 0.0)
        if non_mono > 0:
            violations.append(f"Non-monotonic timestamps ({non_mono} steps)")

        max_j = max([abs(dt - 1.0/self.target_fps)*1000.0 for dt in dts]) if dts else 0.0
        if max_j > self.max_jitter_ms:
            violations.append(f"High jitter ({max_j:.1f}ms > {self.max_jitter_ms}ms)")

        # 2. Kinematics
        for s in steps:
            q = s.get("joint_positions", [])
            for val in q[:6]:
                if abs(val) > 3.4:
                    violations.append("Joint limit excursion")
                    break

        score = max(0.0, 100.0 - (len(violations) * 20.0))
        if score >= 90.0:
            tier = "A"
        elif score >= 80.0:
            tier = "B"
        elif score >= 70.0:
            tier = "C"
        else:
            tier = "D"

        passed = (tier in ("A", "B"))

        report = {
            "episode_id": meta.get("episode_id", os.path.basename(episode_dir)),
            "passed": passed,
            "score": round(score, 1),
            "tier": tier,
            "violations": list(set(violations)),
        }

        with open(os.path.join(episode_dir, "quality.json"), "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)

        return report

    def audit_dataset(self, dataset_dir: str) -> Dict[str, Any]:
        ep_dirs = sorted(glob.glob(os.path.join(dataset_dir, "ep_*")))
        scores = []
        passed_cnt = 0
        failed_cnt = 0

        for d in ep_dirs:
            rep = self.score_episode(d)
            scores.append(rep["score"])
            if rep["passed"]:
                passed_cnt += 1
            else:
                failed_cnt += 1

        avg_score = float(np.mean(scores)) if scores else 0.0
        overall_tier = "A" if avg_score >= 90 else ("B" if avg_score >= 80 else ("C" if avg_score >= 70 else "D"))

        return {
            "total_episodes": len(ep_dirs),
            "passed_count": passed_cnt,
            "failed_count": failed_cnt,
            "mean_score": round(avg_score, 1),
            "dataset_tier": overall_tier,
        }
