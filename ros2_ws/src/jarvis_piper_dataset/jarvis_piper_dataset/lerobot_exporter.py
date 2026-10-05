"""
Hugging Face LeRobot (v2.0) Dataset Exporter for JARVIS PiPER.
Generates compliant metadata, episode manifests, video registries, and data chunks.
"""

import json
import os
import shutil
from typing import Any, Dict, List
import numpy as np


class LeRobotExporter:
    """Exports raw episodes into Hugging Face LeRobot v2.0 dataset format."""

    def __init__(self, output_dir: str, fps: float = 30.0):
        self.output_dir = output_dir
        self.fps = fps
        self.meta_dir = os.path.join(output_dir, "meta")
        self.videos_dir = os.path.join(output_dir, "videos")
        self.data_dir = os.path.join(output_dir, "data", "chunk-000")

        os.makedirs(self.meta_dir, exist_ok=True)
        os.makedirs(self.videos_dir, exist_ok=True)
        os.makedirs(self.data_dir, exist_ok=True)

    def export_dataset(self, episodes_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Converts a list of loaded episode dictionaries into the LeRobot directory layout.
        """
        if not episodes_data:
            return {"total_episodes": 0, "total_frames": 0, "status": "empty"}

        total_frames = 0
        task_set = {}
        episodes_manifest = []

        wrist_video_dir = os.path.join(self.videos_dir, "observation.images.wrist")
        overhead_video_dir = os.path.join(self.videos_dir, "observation.images.overhead")
        os.makedirs(wrist_video_dir, exist_ok=True)
        os.makedirs(overhead_video_dir, exist_ok=True)

        for ep_idx, ep in enumerate(episodes_data):
            meta = ep.get("metadata", {})
            steps = ep.get("timesteps", [])
            ep_id = meta.get("episode_id", f"episode_{ep_idx:06d}")
            task = meta.get("task_instruction", "teleoperated manipulation")

            if task not in task_set:
                task_set[task] = len(task_set)
            task_id = task_set[task]

            T = len(steps)
            total_frames += T

            # 1. Copy videos if available
            raw_dir = meta.get("_source_dir", "")
            raw_wrist_mp4 = os.path.join(raw_dir, "videos", "wrist.mp4")
            raw_overhead_mp4 = os.path.join(raw_dir, "videos", "overhead.mp4")

            dest_wrist = os.path.join(wrist_video_dir, f"episode_{ep_idx:06d}.mp4")
            dest_overhead = os.path.join(overhead_video_dir, f"episode_{ep_idx:06d}.mp4")

            if os.path.exists(raw_wrist_mp4):
                shutil.copyfile(raw_wrist_mp4, dest_wrist)
            if os.path.exists(raw_overhead_mp4):
                shutil.copyfile(raw_overhead_mp4, dest_overhead)

            # 2. Build episode frame data
            # Feature dimensions: 8 state [base_yaw, 6 joints, gripper], 8 action
            frame_records = []
            for t_idx, step in enumerate(steps):
                q = step.get("joint_positions", [0.0] * 6)[:6]
                stroke = step.get("gripper_stroke", 0.035)
                act = step.get("action", q)[:6]

                state_vec = [0.0] + q + [stroke]
                action_vec = [0.0] + act + [stroke]

                record = {
                    "frame_index": t_idx,
                    "timestamp": step.get("timestamp", t_idx / self.fps),
                    "observation.state": state_vec,
                    "action": action_vec,
                    "task_index": task_id,
                }
                frame_records.append(record)

            # Save chunk json
            chunk_file = os.path.join(self.data_dir, f"episode_{ep_idx:06d}.json")
            with open(chunk_file, "w", encoding="utf-8") as f:
                json.dump(frame_records, f)

            episodes_manifest.append({
                "episode_index": ep_idx,
                "episode_id": ep_id,
                "tasks": [task],
                "length": T,
                "success": meta.get("success_label", True),
            })

        # Write meta/info.json
        info_json = {
            "codebase_version": "v2.0",
            "robot_type": "piper",
            "total_episodes": len(episodes_data),
            "total_frames": total_frames,
            "total_tasks": len(task_set),
            "fps": self.fps,
            "features": {
                "observation.state": {
                    "dtype": "float32",
                    "shape": [8],
                    "names": ["base_yaw", "piper_joint1", "piper_joint2", "piper_joint3", "piper_joint4", "piper_joint5", "piper_joint6", "gripper_stroke"],
                },
                "action": {
                    "dtype": "float32",
                    "shape": [8],
                    "names": ["base_yaw", "piper_joint1", "piper_joint2", "piper_joint3", "piper_joint4", "piper_joint5", "piper_joint6", "gripper_stroke"],
                },
                "observation.images.wrist": {
                    "dtype": "video",
                    "shape": [480, 640, 3],
                    "names": ["height", "width", "channel"],
                    "info": {"video.fps": self.fps, "video.codec": "mp4v"},
                },
                "observation.images.overhead": {
                    "dtype": "video",
                    "shape": [480, 640, 3],
                    "names": ["height", "width", "channel"],
                    "info": {"video.fps": self.fps, "video.codec": "mp4v"},
                },
            },
        }

        with open(os.path.join(self.meta_dir, "info.json"), "w", encoding="utf-8") as f:
            json.dump(info_json, f, indent=2)

        # Write meta/episodes.jsonl
        with open(os.path.join(self.meta_dir, "episodes.jsonl"), "w", encoding="utf-8") as f:
            for item in episodes_manifest:
                f.write(json.dumps(item) + "\n")

        # Write meta/tasks.jsonl
        with open(os.path.join(self.meta_dir, "tasks.jsonl"), "w", encoding="utf-8") as f:
            for task_str, task_idx in task_set.items():
                f.write(json.dumps({"task_index": task_idx, "task": task_str}) + "\n")

        return {
            "status": "success",
            "format": "lerobot_v2",
            "output_dir": self.output_dir,
            "total_episodes": len(episodes_data),
            "total_frames": total_frames,
            "total_tasks": len(task_set),
        }
