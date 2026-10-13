"""
Synchronized Multimodal Dataset Recorder for JARVIS Robotics.
Records observations and actions with full schema specification under data/datasets/.
"""

import os
import json
import time
from datetime import datetime
from typing import Dict, Any, List, Optional
import numpy as np

try:
    import cv2
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False


class DatasetEpisodeRecorder:
    """
    Records simulation or physical robot demonstration episodes into standardized format.
    """

    def __init__(self, output_root: str = "data/datasets"):
        self.output_root = output_root
        os.makedirs(self.output_root, exist_ok=True)
        self.current_ep_id: Optional[str] = None
        self.ep_dir: Optional[str] = None
        self.timesteps: List[Dict[str, Any]] = []
        self.video_writer = None
        self.fps = 30.0
        self.start_wall_time = 0.0

    def start_episode(
        self,
        task_id: str = "pick_and_place",
        instruction: str = "Pick up the red cube and place in tray",
        seed: int = 42,
        metadata_extra: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Initializes a new episode recording directory and file handles."""
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.current_ep_id = f"ep_{task_id}_{timestamp_str}_{seed}"
        self.ep_dir = os.path.join(self.output_root, self.current_ep_id)
        os.makedirs(os.path.join(self.ep_dir, "videos"), exist_ok=True)
        os.makedirs(os.path.join(self.ep_dir, "images", "wrist"), exist_ok=True)
        os.makedirs(os.path.join(self.ep_dir, "images", "depth"), exist_ok=True)

        self.timesteps = []
        self.start_wall_time = time.time()

        if HAS_CV2:
            video_path = os.path.join(self.ep_dir, "videos", "wrist.mp4")
            self.video_writer = cv2.VideoWriter(video_path, cv2.VideoWriter_fourcc(*"mp4v"), self.fps, (320, 240))

        self.metadata = {
            "episode_id": self.current_ep_id,
            "task_id": task_id,
            "task_instruction": instruction,
            "random_seed": seed,
            "start_timestamp": datetime.now().isoformat(),
            "simulator_version": "JARVIS_Sim_v1.0 (PhysX-equivalent)",
            "robot_asset_version": "AgileX_PiPER_6DOF_v1.6",
            "schema_version": "2.1.0",
            "target_fps": self.fps,
            "units": {
                "joint_positions": "radians",
                "joint_velocities": "radians/second",
                "gripper_stroke": "meters",
                "tcp_position": "meters",
                "tcp_orientation": "quaternion [x, y, z, w]",
            },
        }
        if metadata_extra:
            self.metadata.update(metadata_extra)

        return self.current_ep_id

    def record_step(
        self,
        step_index: int,
        obs: Dict[str, Any],
        action: List[float],
        timestamp: Optional[float] = None,
        ground_truth: Optional[Dict[str, Any]] = None,
    ):
        """Records a single synchronized timestep."""
        if timestamp is not None:
            elapsed = float(timestamp)
        else:
            elapsed = round(step_index * (1.0 / self.fps), 4)

        rgb = obs.get("rgb")
        depth = obs.get("depth")

        if self.video_writer is not None and rgb is not None:
            self.video_writer.write(rgb)

        if step_index % 10 == 0 and HAS_CV2:
            if rgb is not None:
                cv2.imwrite(os.path.join(self.ep_dir, "images", "wrist", f"frame_{step_index:06d}.jpg"), rgb)
            if depth is not None:
                cv2.imwrite(os.path.join(self.ep_dir, "images", "depth", f"depth_{step_index:06d}.png"), depth)

        step_record = {
            "step_index": step_index,
            "timestamp": elapsed,
            "joint_positions": [round(float(x), 4) for x in obs.get("joint_positions", [])],
            "joint_velocities": [round(float(x), 4) for x in obs.get("joint_velocities", [])],
            "gripper_stroke": round(float(obs.get("gripper_stroke", 0.0)), 4),
            "tcp_pose": obs.get("tcp_pose", {}),
            "action": [round(float(x), 4) for x in action],
            "contact_detected": obs.get("contact_detected", False),
            "object_held": obs.get("object_held", False),
        }
        if ground_truth:
            step_record["ground_truth"] = ground_truth

        self.timesteps.append(step_record)

        # Append to line-by-line crash-resilient journal
        journal_path = os.path.join(self.ep_dir, "stream_journal.jsonl")
        with open(journal_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(step_record) + "\n")

    def end_episode(self, success: bool = True, failure_reason: str = "none") -> Dict[str, Any]:
        """Finalizes episode recording and flushes metadata and trajectory JSON."""
        if self.video_writer is not None:
            self.video_writer.release()
            self.video_writer = None

        total_steps = len(self.timesteps)
        duration_sec = round(time.time() - self.start_wall_time, 2)

        self.metadata.update({
            "end_timestamp": datetime.now().isoformat(),
            "total_steps": total_steps,
            "duration_sec": duration_sec,
            "success_label": bool(success),
            "failure_category": failure_reason,
        })

        with open(os.path.join(self.ep_dir, "metadata.json"), "w", encoding="utf-8") as f:
            json.dump(self.metadata, f, indent=2)

        with open(os.path.join(self.ep_dir, "trajectory.json"), "w", encoding="utf-8") as f:
            json.dump({"metadata": self.metadata, "timesteps": self.timesteps}, f, indent=2)

        return self.metadata
