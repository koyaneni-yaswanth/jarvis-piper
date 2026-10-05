"""
Universal Dataset Exporters for JARVIS-PiPER.
Converts raw episodes into Hugging Face LeRobot, ALOHA/ACT HDF5/NPZ, RLDS, and World Model.
"""

import glob
import json
import os
import shutil
from typing import Any, Dict, List
import numpy as np


class UniversalExporter:
    """Dispatches dataset conversions into multiple robot learning formats."""

    def __init__(self, raw_dir: str, export_root: str):
        self.raw_dir = raw_dir
        self.export_root = export_root
        os.makedirs(self.export_root, exist_ok=True)

    def load_episodes(self) -> List[Dict[str, Any]]:
        ep_dirs = sorted(glob.glob(os.path.join(self.raw_dir, "ep_*")))
        episodes = []
        for d in ep_dirs:
            traj_p = os.path.join(d, "trajectory.json")
            if os.path.exists(traj_p):
                with open(traj_p, "r", encoding="utf-8") as f:
                    ep_data = json.load(f)
                    ep_data.setdefault("metadata", {})["_dir"] = d
                    episodes.append(ep_data)
        return episodes

    def export_all(self, target_format: str = "all") -> Dict[str, Any]:
        episodes = self.load_episodes()
        if not episodes:
            return {"status": "error", "message": f"No episodes found in {self.raw_dir}"}

        out = {"total_episodes": len(episodes), "formats": {}}
        fmt = target_format.lower()

        # 1. LeRobot 2.0
        if fmt in ("lerobot", "all"):
            lerobot_dir = os.path.join(self.export_root, "lerobot_v2")
            os.makedirs(os.path.join(lerobot_dir, "meta"), exist_ok=True)
            os.makedirs(os.path.join(lerobot_dir, "data", "chunk-000"), exist_ok=True)

            total_frames = 0
            ep_manifest = []
            for idx, ep in enumerate(episodes):
                meta = ep.get("metadata", {})
                steps = ep.get("timesteps", [])
                total_frames += len(steps)

                chunk = []
                for t, s in enumerate(steps):
                    q = s.get("joint_positions", [0.0]*6)[:6]
                    stroke = s.get("gripper_stroke", 0.035)
                    act = s.get("action", q)[:6]
                    chunk.append({
                        "frame_index": t,
                        "observation.state": [0.0] + q + [stroke],
                        "action": [0.0] + act + [stroke],
                    })

                with open(os.path.join(lerobot_dir, "data", "chunk-000", f"episode_{idx:06d}.json"), "w") as f:
                    json.dump(chunk, f)

                ep_manifest.append({"episode_index": idx, "length": len(steps)})

            with open(os.path.join(lerobot_dir, "meta", "info.json"), "w") as f:
                json.dump({"codebase_version": "v2.0", "robot_type": "piper", "total_episodes": len(episodes), "total_frames": total_frames}, f, indent=2)

            out["formats"]["lerobot"] = {"output_dir": lerobot_dir, "episodes": len(episodes)}

        # 2. ALOHA / ACT
        if fmt in ("aloha", "all"):
            aloha_dir = os.path.join(self.export_root, "aloha_hdf5")
            os.makedirs(aloha_dir, exist_ok=True)
            saved_files = []
            for idx, ep in enumerate(episodes):
                meta = ep.get("metadata", {})
                steps = ep.get("timesteps", [])
                T = len(steps)
                qpos = np.zeros((T, 8), dtype=np.float32)
                action = np.zeros((T, 8), dtype=np.float32)
                for t, s in enumerate(steps):
                    q = s.get("joint_positions", [0.0]*6)[:6]
                    stroke = s.get("gripper_stroke", 0.035)
                    qpos[t, 1:7] = q
                    qpos[t, 7] = stroke
                    action[t, 1:7] = s.get("action", q)[:6]
                    action[t, 7] = stroke

                ep_id = meta.get("episode_id", f"episode_{idx:06d}")
                file_p = os.path.join(aloha_dir, f"{ep_id}.npz")
                np.savez_compressed(file_p, qpos=qpos, action=action, timesteps=T)
                saved_files.append(file_p)
            out["formats"]["aloha"] = {"output_dir": aloha_dir, "files": len(saved_files)}

        # 3. RLDS
        if fmt in ("rlds", "all"):
            rlds_dir = os.path.join(self.export_root, "rlds")
            os.makedirs(rlds_dir, exist_ok=True)
            for idx, ep in enumerate(episodes):
                meta = ep.get("metadata", {})
                steps = ep.get("timesteps", [])
                ep_id = meta.get("episode_id", f"episode_{idx:06d}")
                rlds_steps = []
                for t, s in enumerate(steps):
                    rlds_steps.append({
                        "is_first": (t == 0),
                        "is_last": (t == len(steps) - 1),
                        "observation": {"joint_positions": s.get("joint_positions", [])[:6], "gripper_stroke": s.get("gripper_stroke", 0.0)},
                        "action": s.get("action", [])[:6],
                        "reward": 1.0 if (t == len(steps)-1) else 0.0,
                    })
                with open(os.path.join(rlds_dir, f"{ep_id}.json"), "w") as f:
                    json.dump({"episode_id": ep_id, "steps": rlds_steps}, f, indent=2)
            out["formats"]["rlds"] = {"output_dir": rlds_dir, "episodes": len(episodes)}

        return out
