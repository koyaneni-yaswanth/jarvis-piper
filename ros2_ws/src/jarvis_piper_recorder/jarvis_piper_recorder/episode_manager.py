"""
JARVIS PiPER Episode Manager
Coordinates episode lifecycle, directory structures, streaming crash-proof journals,
and asynchronous video/telemetry persistence worker threads.
"""

import json
import os
import queue
import re
import shutil
import threading
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np


class EpisodeState:
    IDLE = "IDLE"
    ARMED = "ARMED"
    RECORDING = "RECORDING"
    FINALIZING = "FINALIZING"
    SAVED = "SAVED"
    DISCARDED = "DISCARDED"


class EpisodeWriter:
    """Manages disk writing for a single active episode."""

    def __init__(
        self,
        episode_id: str,
        base_dir: str,
        task_instruction: str,
        operator_id: str,
        task_category: str = "manipulation",
        tags: Optional[List[str]] = None,
        target_fps: float = 30.0,
    ):
        self.episode_id = episode_id
        self.base_dir = base_dir
        self.episode_dir = os.path.join(base_dir, episode_id)
        self.task_instruction = task_instruction
        self.operator_id = operator_id
        self.task_category = task_category
        self.tags = tags or []
        self.target_fps = target_fps

        self.images_wrist_dir = os.path.join(self.episode_dir, "images", "wrist")
        self.images_overhead_dir = os.path.join(self.episode_dir, "images", "overhead")
        self.depth_dir = os.path.join(self.episode_dir, "images", "depth")
        self.videos_dir = os.path.join(self.episode_dir, "videos")

        os.makedirs(self.images_wrist_dir, exist_ok=True)
        os.makedirs(self.images_overhead_dir, exist_ok=True)
        os.makedirs(self.depth_dir, exist_ok=True)
        os.makedirs(self.videos_dir, exist_ok=True)

        self.journal_path = os.path.join(self.episode_dir, "stream_journal.jsonl")
        self._journal_file = open(self.journal_path, "w", buffering=1, encoding="utf-8")

        self.start_wall_time = time.time()
        self.start_iso = datetime.now().isoformat()
        self.recorded_steps: List[Dict[str, Any]] = []

        # Background worker for video/image encoding
        self._work_queue: queue.Queue = queue.Queue(maxsize=1000)
        self._stop_worker = threading.Event()
        self._worker_thread = threading.Thread(target=self._disk_worker, daemon=True)
        self._worker_thread.start()

        self._wrist_video_writer: Optional[cv2.VideoWriter] = None
        self._overhead_video_writer: Optional[cv2.VideoWriter] = None
        self.wrist_video_path = os.path.join(self.videos_dir, "wrist.mp4")
        self.overhead_video_path = os.path.join(self.videos_dir, "overhead.mp4")

    def push_step(
        self,
        step_dict: Dict[str, Any],
        wrist_img: Optional[np.ndarray],
        depth_img: Optional[np.ndarray],
        overhead_img: Optional[np.ndarray],
    ) -> None:
        """Pushes step data into journal and async queue."""
        # Immediate journal write for crash resilience
        line = json.dumps(step_dict) + "\n"
        self._journal_file.write(line)

        self.recorded_steps.append(step_dict)

        # Enqueue heavy image encoding
        item = (
            step_dict["step_index"],
            wrist_img,
            depth_img,
            overhead_img,
        )
        try:
            self._work_queue.put_nowait(item)
        except queue.Full:
            pass  # Drops are handled gracefully if queue overflows

    def _disk_worker(self) -> None:
        """Background thread executing video compression and image saves."""
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")

        while not self._stop_worker.is_set() or not self._work_queue.empty():
            try:
                item = self._work_queue.get(timeout=0.1)
            except queue.Empty:
                continue

            step_idx, wrist_img, depth_img, overhead_img = item

            # 1. Wrist Camera Frame
            if wrist_img is not None and wrist_img.size > 0:
                h, w = wrist_img.shape[:2]
                if self._wrist_video_writer is None:
                    self._wrist_video_writer = cv2.VideoWriter(
                        self.wrist_video_path, fourcc, self.target_fps, (w, h)
                    )
                self._wrist_video_writer.write(wrist_img)
                # Also save individual keyframe for instant preview
                if step_idx % 10 == 0:
                    cv2.imwrite(
                        os.path.join(self.images_wrist_dir, f"frame_{step_idx:06d}.jpg"),
                        wrist_img,
                        [int(cv2.IMWRITE_JPEG_QUALITY), 90],
                    )

            # 2. Overhead Camera Frame
            if overhead_img is not None and overhead_img.size > 0:
                h, w = overhead_img.shape[:2]
                if self._overhead_video_writer is None:
                    self._overhead_video_writer = cv2.VideoWriter(
                        self.overhead_video_path, fourcc, self.target_fps, (w, h)
                    )
                self._overhead_video_writer.write(overhead_img)
                if step_idx % 10 == 0:
                    cv2.imwrite(
                        os.path.join(self.images_overhead_dir, f"frame_{step_idx:06d}.jpg"),
                        overhead_img,
                        [int(cv2.IMWRITE_JPEG_QUALITY), 90],
                    )

            # 3. Depth Map (16-bit PNG)
            if depth_img is not None and depth_img.size > 0:
                if step_idx % 5 == 0:
                    depth_path = os.path.join(self.depth_dir, f"depth_{step_idx:06d}.png")
                    cv2.imwrite(depth_path, depth_img)

            self._work_queue.task_done()

        if self._wrist_video_writer is not None:
            self._wrist_video_writer.release()
        if self._overhead_video_writer is not None:
            self._overhead_video_writer.release()

    def finalize(self, success_label: bool = True, notes: str = "") -> Dict[str, Any]:
        """Flushes queue, closes journal, and writes complete trajectory & metadata JSONs."""
        self._journal_file.close()

        # Stop worker and wait for remaining writes
        self._stop_worker.set()
        if self._worker_thread.is_alive():
            self._worker_thread.join(timeout=5.0)

        end_wall_time = time.time()
        duration_sec = end_wall_time - self.start_wall_time
        end_iso = datetime.now().isoformat()

        metadata = {
            "episode_id": self.episode_id,
            "task_instruction": self.task_instruction,
            "task_category": self.task_category,
            "operator_id": self.operator_id,
            "source_label": "DEMONSTRATION",
            "robot_platform": "PiPER_6DOF",
            "success_label": bool(success_label),
            "notes": notes,
            "duration_sec": round(duration_sec, 3),
            "total_steps": len(self.recorded_steps),
            "target_fps": self.target_fps,
            "start_timestamp": self.start_iso,
            "end_timestamp": end_iso,
            "tags": self.tags,
            "schema_version": "2.0.0",
        }

        # Write metadata.json
        meta_path = os.path.join(self.episode_dir, "metadata.json")
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)

        # Write trajectory.json (structured full episode)
        full_trajectory = {
            "metadata": metadata,
            "timesteps": self.recorded_steps,
        }
        traj_path = os.path.join(self.episode_dir, "trajectory.json")
        with open(traj_path, "w", encoding="utf-8") as f:
            json.dump(full_trajectory, f, indent=2)

        return metadata

    def discard(self) -> None:
        """Discards episode and deletes directory."""
        self._journal_file.close()
        self._stop_worker.set()
        if self._worker_thread.is_alive():
            self._worker_thread.join(timeout=2.0)
        if os.path.exists(self.episode_dir):
            shutil.rmtree(self.episode_dir, ignore_errors=True)
