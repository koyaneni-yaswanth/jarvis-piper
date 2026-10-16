#!/usr/bin/env python3
"""
JARVIS-PiPER: Live Observation Replay & HDF5 Export Tool.
Offline replay, inspection, and canonical dataset conversion for recorded live observations:
- Inspect recorded telemetry, joint distributions, and frame counts
- Step-by-step telemetry stream playback (read-only, no robot actuation)
- Conversion to standard HDF5 format for V-JEPA / policy learning

Usage:
    python tools/live_replay.py data/recordings/live_obs_YYYYMMDD_HHMMSS --info
    python tools/live_replay.py data/recordings/live_obs_YYYYMMDD_HHMMSS --export-hdf5 episode_001.h5
    python tools/live_replay.py data/recordings/live_obs_YYYYMMDD_HHMMSS --stream --speed 2.0
"""

import sys
import os
import json
import time
import argparse
from pathlib import Path
from typing import Dict, Any, List, Optional, Iterator
import numpy as np

try:
    import cv2
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False

try:
    import h5py
    HAS_H5PY = True
except ImportError:
    HAS_H5PY = False


class LiveObservationReplayer:
    """
    Offline inspector and exporter for live physical observation recordings.
    Guaranteed read-only: does not connect to CAN or command robot motion.
    """

    def __init__(self, session_dir: str | Path):
        self.session_path = Path(session_dir)
        if not self.session_path.is_dir():
            raise FileNotFoundError(f"Session directory not found: {self.session_path}")

        meta_path = self.session_path / "metadata.json"
        telem_path = self.session_path / "telemetry.jsonl"

        if not meta_path.is_file():
            raise FileNotFoundError(f"Missing metadata.json in {self.session_path}")
        if not telem_path.is_file():
            raise FileNotFoundError(f"Missing telemetry.jsonl in {self.session_path}")

        with open(meta_path, "r", encoding="utf-8") as f:
            self.metadata = json.load(f)

        self.records: List[Dict[str, Any]] = []
        with open(telem_path, "r", encoding="utf-8") as f:
            for line in f:
                line_str = line.strip()
                if line_str:
                    self.records.append(json.loads(line_str))

    @property
    def total_steps(self) -> int:
        return len(self.records)

    def get_summary(self) -> Dict[str, Any]:
        """Calculates statistical summary of the recorded session."""
        summary = {
            "session_id": self.metadata.get("session_id", self.session_path.name),
            "task_description": self.metadata.get("task_description", "N/A"),
            "operator": self.metadata.get("operator", "N/A"),
            "created_at_utc": self.metadata.get("created_at_utc", "N/A"),
            "total_steps": len(self.records),
            "duration_s": self.metadata.get("actual_duration_seconds", 0.0),
            "target_control_hz": self.metadata.get("target_control_hz", 30.0),
            "effective_hz": self.metadata.get("effective_hz", 0.0),
            "modalities": {},
        }

        if not self.records:
            return summary

        # Robot joints summary
        joints = [r["joint_positions"] for r in self.records if "joint_positions" in r]
        if joints:
            j_arr = np.array(joints)
            summary["modalities"]["robot_joints"] = {
                "count": len(joints),
                "min_rad": np.round(np.min(j_arr, axis=0), 4).tolist(),
                "max_rad": np.round(np.max(j_arr, axis=0), 4).tolist(),
                "mean_rad": np.round(np.mean(j_arr, axis=0), 4).tolist(),
            }

        # Gripper summary
        grippers = [r["gripper_stroke_m"] for r in self.records if "gripper_stroke_m" in r]
        if grippers:
            summary["modalities"]["gripper_stroke"] = {
                "count": len(grippers),
                "min_m": round(float(np.min(grippers)), 4),
                "max_m": round(float(np.max(grippers)), 4),
            }

        # Camera frame summaries
        wrist_imgs = [r["wrist_color_file"] for r in self.records if "wrist_color_file" in r]
        depth_imgs = [r["wrist_depth_file"] for r in self.records if "wrist_depth_file" in r]
        oh_imgs = [r["overhead_color_file"] for r in self.records if "overhead_color_file" in r]
        pika_recs = [r["pika_sense"] for r in self.records if "pika_sense" in r]

        summary["modalities"]["wrist_color_frames"] = len(wrist_imgs)
        summary["modalities"]["wrist_depth_frames"] = len(depth_imgs)
        summary["modalities"]["overhead_color_frames"] = len(oh_imgs)
        summary["modalities"]["pika_sense_samples"] = len(pika_recs)

        return summary

    def stream_steps(self, playback_speed: float = 1.0) -> Iterator[Dict[str, Any]]:
        """Yields records in order with simulated playback pacing."""
        if not self.records:
            return

        t_prev = self.records[0].get("timestamp_s", 0.0)
        for r in self.records:
            t_curr = r.get("timestamp_s", t_prev)
            dt = t_curr - t_prev
            if playback_speed > 0 and dt > 0:
                time.sleep(dt / playback_speed)
            t_prev = t_curr
            yield r

    def export_to_hdf5(self, output_file: str | Path) -> Path:
        """
        Exports the recorded live session into a standardized canonical HDF5 file.
        Includes robot telemetry, synchronized depth, and color observation arrays.
        """
        if not HAS_H5PY:
            raise RuntimeError("h5py is not installed in the current environment.")

        out_path = Path(output_file)
        out_path.parent.mkdir(parents=True, exist_ok=True)

        n_steps = len(self.records)
        if n_steps == 0:
            raise ValueError("No records to export.")

        timestamps = np.array([r.get("timestamp_s", 0.0) for r in self.records], dtype=np.float64)
        monotonic_ns = np.array([r.get("monotonic_ns", 0) for r in self.records], dtype=np.int64)

        with h5py.File(str(out_path), "w") as h5:
            # Metadata attributes
            h5.attrs["session_id"] = str(self.metadata.get("session_id", self.session_path.name))
            h5.attrs["task_description"] = str(self.metadata.get("task_description", ""))
            h5.attrs["operator"] = str(self.metadata.get("operator", "operator"))
            h5.attrs["target_control_hz"] = float(self.metadata.get("target_control_hz", 30.0))
            h5.attrs["actual_duration_seconds"] = float(self.metadata.get("actual_duration_seconds", 0.0))
            h5.attrs["total_timesteps"] = int(n_steps)

            # Timestamps
            h5.create_dataset("timestamps", data=timestamps, compression="gzip")
            h5.create_dataset("monotonic_ns", data=monotonic_ns, compression="gzip")

            obs_grp = h5.create_group("observations")

            # 1. Robot Joints & TCP
            joints = [r.get("joint_positions") for r in self.records if "joint_positions" in r]
            if len(joints) == n_steps:
                obs_grp.create_dataset("joint_positions", data=np.array(joints, dtype=np.float32), compression="gzip")

            grippers = [r.get("gripper_stroke_m") for r in self.records if "gripper_stroke_m" in r]
            if len(grippers) == n_steps:
                obs_grp.create_dataset("gripper_stroke_m", data=np.array(grippers, dtype=np.float32), compression="gzip")

            tcp_pos = [r.get("tcp_pose", {}).get("position_m") for r in self.records if "tcp_pose" in r]
            tcp_rpy = [r.get("tcp_pose", {}).get("rpy_rad") for r in self.records if "tcp_pose" in r]
            if len(tcp_pos) == n_steps and None not in tcp_pos:
                obs_grp.create_dataset("tcp_position_m", data=np.array(tcp_pos, dtype=np.float32), compression="gzip")
                obs_grp.create_dataset("tcp_rpy_rad", data=np.array(tcp_rpy, dtype=np.float32), compression="gzip")

            vels = [r.get("joint_velocities") for r in self.records if "joint_velocities" in r]
            if len(vels) == n_steps:
                obs_grp.create_dataset("joint_velocities", data=np.array(vels, dtype=np.float32), compression="gzip")

            efforts = [r.get("joint_efforts") for r in self.records if "joint_efforts" in r]
            if len(efforts) == n_steps:
                obs_grp.create_dataset("joint_efforts", data=np.array(efforts, dtype=np.float32), compression="gzip")

            actions = [r.get("action") for r in self.records if "action" in r and r.get("action") is not None]
            if len(actions) == n_steps:
                if isinstance(actions[0], list):
                    h5.create_dataset("action", data=np.array(actions, dtype=np.float32), compression="gzip")
                elif isinstance(actions[0], dict) and "values" in actions[0]:
                    act_vals = [a["values"] for a in actions]
                    h5.create_dataset("action", data=np.array(act_vals, dtype=np.float32), compression="gzip")

            # 2. PIKA Sense
            pika_data = [r.get("pika_sense") for r in self.records if "pika_sense" in r]
            if len(pika_data) == n_steps:
                pika_grp = obs_grp.create_group("pika_sense")
                pika_grp.create_dataset(
                    "encoder_rad",
                    data=np.array([p.get("encoder_rad", 0.0) for p in pika_data], dtype=np.float32),
                    compression="gzip",
                )
                pika_grp.create_dataset(
                    "gripper_distance_mm",
                    data=np.array([p.get("gripper_distance_mm", 0.0) for p in pika_data], dtype=np.float32),
                    compression="gzip",
                )
                pika_grp.create_dataset(
                    "trigger_state",
                    data=np.array([p.get("command_trigger_state", 0) for p in pika_data], dtype=np.int32),
                    compression="gzip",
                )

            # 3. Images (load and store arrays if CV2 available)
            if HAS_CV2:
                # Wrist Color
                wrist_paths = [self.session_path / r["wrist_color_file"] for r in self.records if "wrist_color_file" in r]
                if len(wrist_paths) == n_steps and all(p.is_file() for p in wrist_paths):
                    first_img = cv2.imread(str(wrist_paths[0]))
                    if first_img is not None:
                        h, w, c = first_img.shape
                        ds = obs_grp.create_dataset("wrist_color", shape=(n_steps, h, w, c), dtype=np.uint8, compression="gzip")
                        for idx, p in enumerate(wrist_paths):
                            img = cv2.imread(str(p))
                            ds[idx] = img

                # Wrist Depth (lossless uint16 mm)
                depth_paths = [self.session_path / r["wrist_depth_file"] for r in self.records if "wrist_depth_file" in r]
                if len(depth_paths) == n_steps and all(p.is_file() for p in depth_paths):
                    first_d = cv2.imread(str(depth_paths[0]), cv2.IMREAD_UNCHANGED)
                    if first_d is not None:
                        h, w = first_d.shape
                        ds = obs_grp.create_dataset("wrist_depth", shape=(n_steps, h, w), dtype=np.uint16, compression="gzip")
                        for idx, p in enumerate(depth_paths):
                            d_arr = cv2.imread(str(p), cv2.IMREAD_UNCHANGED)
                            ds[idx] = d_arr

                # Overhead Color
                oh_paths = [self.session_path / r["overhead_color_file"] for r in self.records if "overhead_color_file" in r]
                if len(oh_paths) == n_steps and all(p.is_file() for p in oh_paths):
                    first_oh = cv2.imread(str(oh_paths[0]))
                    if first_oh is not None:
                        h, w, c = first_oh.shape
                        ds = obs_grp.create_dataset("overhead_color", shape=(n_steps, h, w, c), dtype=np.uint8, compression="gzip")
                        for idx, p in enumerate(oh_paths):
                            img = cv2.imread(str(p))
                            ds[idx] = img

                # Aliases for downstream demonstration dataset compatibility
                img_grp = obs_grp.create_group("images")
                if "wrist_color" in obs_grp:
                    img_grp["color"] = obs_grp["wrist_color"]
                if "wrist_depth" in obs_grp:
                    img_grp["depth"] = obs_grp["wrist_depth"]
                if "overhead_color" in obs_grp:
                    img_grp["fisheye"] = obs_grp["overhead_color"]

            # Canonical observations/qpos (for direct downstream policy training)
            tracker_poses = [r.get("pika_tracker_pose") for r in self.records if "pika_tracker_pose" in r]
            if len(tracker_poses) == n_steps and len(pika_data) == n_steps:
                qpos_list = []
                for tp, pd in zip(tracker_poses, pika_data):
                    pos = tp.get("position", [0.0, 0.0, 0.0])
                    rot = tp.get("rotation", [0.0, 0.0, 0.0, 1.0])
                    grip = pd.get("gripper_distance_mm", 0.0)
                    qpos_list.append(list(pos[:3]) + list(rot[:4]) + [float(grip)])
                obs_grp.create_dataset("qpos", data=np.array(qpos_list, dtype=np.float32), compression="gzip")
            elif len(joints) == n_steps:
                if len(grippers) == n_steps:
                    j_qpos = [list(j) + [g * 1000.0] for j, g in zip(joints, grippers)]
                    obs_grp.create_dataset("qpos", data=np.array(j_qpos, dtype=np.float32), compression="gzip")

        return out_path


def main():
    parser = argparse.ArgumentParser(description="JARVIS-PiPER Live Observation Replay & Exporter")
    parser.add_argument("session_dir", type=str, help="Path to live recording session directory")
    parser.add_argument("--info", action="store_true", default=True, help="Display session summary information")
    parser.add_argument("--export-hdf5", type=str, default=None, help="Export session to canonical HDF5 file")
    parser.add_argument("--stream", action="store_true", help="Simulate telemetry stream playback")
    parser.add_argument("--speed", type=float, default=1.0, help="Playback speed multiplier (0 = instant)")
    parser.add_argument("--json-out", type=str, default=None, help="Save summary report to JSON")
    args = parser.parse_args()

    replayer = LiveObservationReplayer(args.session_dir)
    summary = replayer.get_summary()

    print("=" * 80)
    print("      JARVIS-PiPER :: LIVE OBSERVATION REPLAY & INSPECTION")
    print(f" Session ID: {summary['session_id']}")
    print(f" Duration  : {summary['duration_s']}s ({summary['total_steps']} steps @ {summary['effective_hz']} Hz)")
    print("=" * 80)

    print("\n Modal Information:")
    for mod_name, mod_info in summary["modalities"].items():
        if isinstance(mod_info, dict):
            print(f"  - {mod_name}:")
            for k, v in mod_info.items():
                print(f"      {k}: {v}")
        else:
            print(f"  - {mod_name}: {mod_info}")

    if args.export_hdf5:
        print(f"\n[INFO] Exporting session to HDF5: {args.export_hdf5} ...")
        out_p = replayer.export_to_hdf5(args.export_hdf5)
        print(f"[PASS] Successfully exported HDF5 dataset: {out_p.resolve()}")

    if args.stream:
        print(f"\n[INFO] Streaming playback at {args.speed:.1f}x speed (Ctrl+C to abort)...")
        try:
            for s in replayer.stream_steps(playback_speed=args.speed):
                step = s.get("step", 0)
                t = s.get("timestamp_s", 0.0)
                q = s.get("joint_positions", [])
                q_str = f"[{', '.join(f'{x:.2f}' for x in q)}]" if q else "N/A"
                print(f"\r Step {step:05d} | t={t:06.2f}s | Q={q_str}", end="", flush=True)
            print("\n[INFO] Stream playback completed.")
        except KeyboardInterrupt:
            print("\n[INFO] Stream playback interrupted by user.")

    if args.json_out:
        with open(args.json_out, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2)
        print(f"\nSummary JSON saved to {args.json_out}")


if __name__ == "__main__":
    main()
