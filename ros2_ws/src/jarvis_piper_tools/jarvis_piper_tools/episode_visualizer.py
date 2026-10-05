"""
JARVIS PiPER Episode Visualizer CLI
Inspects recorded episode trajectories, joint curves, and video keyframes.
"""

import argparse
import json
import os
import sys


def visualize_episode(ep_dir: str):
    traj_path = os.path.join(ep_dir, "trajectory.json")
    if not os.path.exists(traj_path):
        print(f"[ERR] No trajectory.json found in {ep_dir}")
        return 1

    with open(traj_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    meta = data.get("metadata", {})
    steps = data.get("timesteps", [])

    print("=" * 80)
    print(f"       JARVIS PiPER EPISODE INSPECTION: {meta.get('episode_id', 'unknown')}")
    print("=" * 80)
    print(f"  Task:        {meta.get('task_instruction')}")
    print(f"  Operator:    {meta.get('operator_id')}")
    print(f"  Success:     {meta.get('success_label')}")
    print(f"  Duration:    {meta.get('duration_sec', 0.0):.2f}s")
    print(f"  Total Steps: {len(steps)}")
    print(f"  Start Time:  {meta.get('start_timestamp')}")
    print(f"  End Time:    {meta.get('end_timestamp')}")
    print("-" * 80)

    # Sample steps preview
    print(f" {'Step':^6} | {'Time (s)':^8} | {'q1':^7} {'q2':^7} {'q3':^7} {'q4':^7} {'q5':^7} {'q6':^7} | {'Stroke':^8}")
    print("-" * 80)
    sample_indices = [0, len(steps)//4, len(steps)//2, (3*len(steps))//4, len(steps)-1] if len(steps) >= 5 else range(len(steps))
    for idx in sample_indices:
        if 0 <= idx < len(steps):
            s = steps[idx]
            t = s.get("timestamp", 0.0)
            q = s.get("joint_positions", [0.0]*6)[:6]
            stroke = s.get("gripper_stroke", 0.0)
            q_str = " ".join([f"{val:+.3f}" for val in q])
            print(f" {idx:6d} | {t:8.3f} | {q_str} | {stroke:8.4f}")

    print("=" * 80)
    return 0


def main():
    parser = argparse.ArgumentParser(description="JARVIS PiPER Episode Visualizer")
    parser.add_argument("episode_dir", help="Path to episode directory")
    args = parser.parse_args()
    return visualize_episode(args.episode_dir)


if __name__ == "__main__":
    sys.exit(main())
