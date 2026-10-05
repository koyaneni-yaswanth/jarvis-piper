"""
Master Dataset Export Pipeline for JARVIS PiPER.
Dispatches episodes to LeRobot, ALOHA HDF5, RLDS, and World Model formats.
"""

import argparse
import glob
import json
import os
import sys
from typing import Any, Dict, List

from jarvis_piper_dataset.lerobot_exporter import LeRobotExporter
from jarvis_piper_dataset.aloha_hdf5_exporter import AlohaHdf5Exporter
from jarvis_piper_dataset.rlds_exporter import RldsExporter
from jarvis_piper_world_model.transition_builder import TransitionDatasetBuilder


class DatasetExportPipeline:
    """Master pipeline managing multi-format conversions."""

    def __init__(self, raw_episodes_dir: str, export_root_dir: str):
        self.raw_episodes_dir = raw_episodes_dir
        self.export_root_dir = export_root_dir
        os.makedirs(self.export_root_dir, exist_ok=True)

    def load_episodes(self) -> List[Dict[str, Any]]:
        """Loads all raw episode directories containing trajectory.json."""
        episodes = []
        ep_dirs = sorted(glob.glob(os.path.join(self.raw_episodes_dir, "ep_*")))

        for d in ep_dirs:
            traj_path = os.path.join(d, "trajectory.json")
            if os.path.exists(traj_path):
                try:
                    with open(traj_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        data.setdefault("metadata", {})["_source_dir"] = d
                        episodes.append(data)
                except Exception as e:
                    print(f"[WARN] Failed loading {traj_path}: {e}")

        return episodes

    def export(self, target_format: str = "all") -> Dict[str, Any]:
        """Runs exports for specified format ('lerobot', 'aloha', 'rlds', 'world_model', 'all')."""
        episodes = self.load_episodes()
        if not episodes:
            return {"status": "error", "message": f"No valid episodes found in {self.raw_episodes_dir}"}

        results = {"total_episodes": len(episodes), "formats": {}}

        fmt = target_format.lower()
        if fmt in ("lerobot", "all"):
            lerobot_dir = os.path.join(self.export_root_dir, "lerobot_v2")
            exporter = LeRobotExporter(output_dir=lerobot_dir)
            results["formats"]["lerobot"] = exporter.export_dataset(episodes)

        if fmt in ("aloha", "hdf5", "all"):
            aloha_dir = os.path.join(self.export_root_dir, "aloha_hdf5")
            exporter = AlohaHdf5Exporter(output_dir=aloha_dir)
            results["formats"]["aloha"] = exporter.export_dataset(episodes)

        if fmt in ("rlds", "all"):
            rlds_dir = os.path.join(self.export_root_dir, "rlds")
            exporter = RldsExporter(output_dir=rlds_dir)
            results["formats"]["rlds"] = exporter.export_dataset(episodes)

        if fmt in ("world_model", "all"):
            wm_dir = os.path.join(self.export_root_dir, "world_model")
            os.makedirs(wm_dir, exist_ok=True)
            builder = TransitionDatasetBuilder()
            wm_files = []
            for ep in episodes:
                try:
                    t_dict = builder.build_transitions(ep)
                    ep_id = t_dict["episode_id"]
                    save_path = os.path.join(wm_dir, f"{ep_id}_transitions.npz")
                    import numpy as np
                    np.savez_compressed(
                        save_path,
                        observations=t_dict["observations"],
                        actions=t_dict["actions"],
                        rewards=t_dict["rewards"],
                        next_observations=t_dict["next_observations"],
                        terminals=t_dict["terminals"],
                        language_instruction=t_dict["language_instruction"],
                    )
                    wm_files.append(save_path)
                except Exception as e:
                    print(f"[WARN] Failed building transitions for episode: {e}")
            results["formats"]["world_model"] = {"status": "success", "files": wm_files}

        return results


def main():
    parser = argparse.ArgumentParser(description="JARVIS PiPER Dataset Export CLI")
    parser.add_argument(
        "--input-dir",
        default="/mnt/d/yaswanth/ranger mini/jarvis_piper_ws/data/raw_episodes",
        help="Path to raw episodes directory",
    )
    parser.add_argument(
        "--output-dir",
        default="/mnt/d/yaswanth/ranger mini/jarvis_piper_ws/data/exports",
        help="Path to export root directory",
    )
    parser.add_argument(
        "--format",
        default="all",
        choices=["all", "lerobot", "aloha", "rlds", "world_model"],
        help="Target export format",
    )
    args = parser.parse_args()

    print("=" * 80)
    print("      JARVIS PiPER UNIVERSAL DATASET EXPORT PIPELINE")
    print(f"  Input:  {args.input_dir}")
    print(f"  Output: {args.output_dir}")
    print(f"  Format: {args.format}")
    print("=" * 80)

    pipeline = DatasetExportPipeline(args.input_dir, args.output_dir)
    res = pipeline.export(args.format)

    print("\n[RESULT]")
    print(json.dumps(res, indent=2))
    print("=" * 80)
    return 0


if __name__ == "__main__":
    sys.exit(main())
