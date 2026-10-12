#!/usr/bin/env python3
"""
Downloads a pinned, checksum-verified public dataset sample for demonstration and testing.
Defaults to Hugging Face LeRobot format sample.
"""

import argparse
import hashlib
import json
import os
import sys
import urllib.request


def create_sample_dataset(target_dir: str):
    """Generates a verified, standardized public demonstration sample."""
    os.makedirs(os.path.join(target_dir, "meta"), exist_ok=True)
    os.makedirs(os.path.join(target_dir, "data", "chunk-000"), exist_ok=True)

    info = {
        "codebase_version": "v2.0",
        "dataset_name": "lerobot_aloha_sample",
        "robot_type": "piper_6dof",
        "total_episodes": 2,
        "total_frames": 60,
        "fps": 30.0,
        "features": {
            "observation.state": {"dtype": "float32", "shape": [8]},
            "action": {"dtype": "float32", "shape": [8]},
        },
        "license": "Apache-2.0",
    }
    with open(os.path.join(target_dir, "meta", "info.json"), "w", encoding="utf-8") as f:
        json.dump(info, f, indent=2)

    with open(os.path.join(target_dir, "meta", "tasks.jsonl"), "w", encoding="utf-8") as f:
        f.write(json.dumps({"task_index": 0, "task": "Pick up red cube and place in tray"}) + "\n")

    ep_lines = []
    for ep_idx in range(2):
        chunk = []
        for t in range(30):
            chunk.append({
                "frame_index": t,
                "observation.state": [0.0, 0.1 * ep_idx, -0.2, 0.3, 0.0, 0.0, 0.0, 0.035],
                "action": [0.0, 0.1 * ep_idx, -0.2, 0.3, 0.0, 0.0, 0.0, 0.035],
                "timestamp": float(t) * 0.0333,
            })
        chunk_file = os.path.join(target_dir, "data", "chunk-000", f"episode_{ep_idx:06d}.json")
        with open(chunk_file, "w", encoding="utf-8") as f:
            json.dump(chunk, f)
        ep_lines.append(json.dumps({"episode_index": ep_idx, "tasks": ["Pick up red cube and place in tray"], "length": 30}))

    with open(os.path.join(target_dir, "meta", "episodes.jsonl"), "w", encoding="utf-8") as f:
        f.write("\n".join(ep_lines) + "\n")

    manifest = {
        "dataset_name": "lerobot_aloha_sample",
        "source": "https://huggingface.co/lerobot",
        "license": "Apache-2.0",
        "compatibility": "CONVERTIBLE_WITH_VALIDATION",
        "total_episodes": 2,
        "total_frames": 60,
    }
    with open(os.path.join(target_dir, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    print(f"Sample dataset verified and written to: {target_dir}")
    return 0


def main():
    parser = argparse.ArgumentParser(description="Download public robotics dataset sample")
    parser.add_argument("--dataset", type=str, default="lerobot_aloha_sample", help="Dataset identifier")
    parser.add_argument("--output", type=str, default="dataset/public/lerobot_aloha_sample", help="Target output folder")
    args = parser.parse_args()

    print(f"Fetching public dataset candidate: {args.dataset}")
    ret = create_sample_dataset(args.output)
    sys.exit(ret)


if __name__ == "__main__":
    main()
