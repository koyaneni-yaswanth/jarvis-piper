"""
RLDS / Open X-Embodiment Dataset Exporter for JARVIS PiPER.
Transforms episode trajectories into standardized RLDS step dictionaries.
"""

import json
import os
from typing import Any, Dict, List


class RldsExporter:
    """Exports episodes into Open X-Embodiment / RLDS format."""

    def __init__(self, output_dir: str):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    def export_episode(self, episode_data: Dict[str, Any]) -> str:
        meta = episode_data.get("metadata", {})
        steps = episode_data.get("timesteps", [])
        ep_id = meta.get("episode_id", "unknown_episode")
        task = meta.get("task_instruction", "")
        success = meta.get("success_label", True)
        T = len(steps)

        rlds_steps = []
        for idx, s in enumerate(steps):
            is_first = (idx == 0)
            is_last = (idx == T - 1)
            is_terminal = is_last and success

            reward = 1.0 if (is_last and success) else 0.0
            discount = 0.0 if is_terminal else 1.0

            q = s.get("joint_positions", [0.0] * 6)[:6]
            stroke = s.get("gripper_stroke", 0.035)
            act = s.get("action", q)[:6]

            step_record = {
                "is_first": is_first,
                "is_last": is_last,
                "is_terminal": is_terminal,
                "observation": {
                    "natural_language_instruction": task,
                    "joint_positions": q,
                    "gripper_position": stroke,
                    "tcp_pose": s.get("tcp_pose", {}),
                },
                "action": {
                    "joint_targets": act,
                    "gripper_target": stroke,
                },
                "reward": reward,
                "discount": discount,
                "timestamp": s.get("timestamp", idx * 0.033),
            }
            rlds_steps.append(step_record)

        rlds_episode = {
            "episode_id": ep_id,
            "metadata": meta,
            "steps": rlds_steps,
        }

        out_path = os.path.join(self.output_dir, f"{ep_id}_rlds.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(rlds_episode, f, indent=2)
        return out_path

    def export_dataset(self, episodes_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        paths = [self.export_episode(ep) for ep in episodes_data]
        return {
            "status": "success",
            "format": "rlds",
            "output_dir": self.output_dir,
            "total_episodes": len(episodes_data),
            "files": paths,
        }
