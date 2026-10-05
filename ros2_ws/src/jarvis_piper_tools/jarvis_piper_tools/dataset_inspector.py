"""
JARVIS PiPER Dataset Statistics & Integrity Inspector CLI
Analyzes aggregate statistics, duration distributions, and action coverage across dataset.
"""

import argparse
import glob
import json
import os
import sys
import numpy as np


def inspect_dataset(dataset_dir: str):
    ep_dirs = sorted(glob.glob(os.path.join(dataset_dir, "ep_*")))
    if not ep_dirs:
        print(f"[ERR] No episodes found in {dataset_dir}")
        return 1

    durations = []
    step_counts = []
    tasks = set()
    operators = set()
    success_count = 0
    all_q = []

    for d in ep_dirs:
        traj_p = os.path.join(d, "trajectory.json")
        if os.path.exists(traj_p):
            with open(traj_p, "r", encoding="utf-8") as f:
                data = json.load(f)
            meta = data.get("metadata", {})
            steps = data.get("timesteps", [])

            durations.append(meta.get("duration_sec", 0.0))
            step_counts.append(len(steps))
            tasks.add(meta.get("task_instruction", ""))
            operators.add(meta.get("operator_id", ""))
            if meta.get("success_label", True):
                success_count += 1

            for s in steps:
                q = s.get("joint_positions", [])[:6]
                if len(q) == 6:
                    all_q.append(q)

    print("=" * 80)
    print("           JARVIS PiPER DATASET AGGREGATE SUMMARY & AUDIT")
    print(f"  Dataset Directory: {dataset_dir}")
    print("=" * 80)
    print(f"  Total Episodes:        {len(ep_dirs)}")
    print(f"  Success Rate:          {success_count / len(ep_dirs) * 100:.1f}% ({success_count}/{len(ep_dirs)})")
    print(f"  Total Frames Recorded: {sum(step_counts)}")
    print(f"  Total Duration:        {sum(durations):.1f}s ({sum(durations)/3600.0:.2f} hrs)")
    print(f"  Mean Episode Duration: {np.mean(durations):.2f}s (Min: {np.min(durations):.2f}s, Max: {np.max(durations):.2f}s)")
    print(f"  Mean Steps/Episode:    {np.mean(step_counts):.1f} steps")
    print(f"  Unique Tasks ({len(tasks)}):")
    for t in sorted(tasks)[:5]:
        print(f"    - {t}")
    if len(tasks) > 5:
        print(f"    ... and {len(tasks)-5} more.")

    if all_q:
        q_arr = np.array(all_q)
        print("-" * 80)
        print("  Joint Range Coverage (Min / Mean / Max in rad):")
        for j in range(6):
            print(f"    Joint {j+1}: Min: {np.min(q_arr[:, j]):+.3f} | Mean: {np.mean(q_arr[:, j]):+.3f} | Max: {np.max(q_arr[:, j]):+.3f}")

    print("=" * 80)
    return 0


def main():
    parser = argparse.ArgumentParser(description="JARVIS PiPER Dataset Inspector")
    parser.add_argument(
        "--dataset-dir",
        default="/mnt/d/yaswanth/ranger mini/jarvis_piper_ws/data/raw_episodes",
        help="Path to dataset directory",
    )
    args = parser.parse_args()
    return inspect_dataset(args.dataset_dir)


if __name__ == "__main__":
    sys.exit(main())
