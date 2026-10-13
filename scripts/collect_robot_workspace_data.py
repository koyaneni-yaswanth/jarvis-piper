#!/usr/bin/env python3
"""
collect_robot_workspace_data.py

Comprehensive workspace data collection & forensic inventory tool for
Piper 6-DOF Robotic Arm + PIKA Sense + ROS 2 + V-JEPA Embodied AI platform.

Scans:
- Physical data/database/benchmark directories
- Pika packages, PIKA Sense configs, SteamVR rules
- RealSense / MCAP recording tools & compressed camera nodes
- Video archives, image datasets, and joint telemetry
- Trained weights, YOLO detectors, and V-JEPA checkpoints
- URDF, Xacro, SRDF, MoveIt 2, and ros2_control configs

Usage:
    python3 scripts/collect_robot_workspace_data.py --inventory-only
    python3 scripts/collect_robot_workspace_data.py
    python3 scripts/collect_robot_workspace_data.py --output-dir my_collection --max-file-mb 50
"""

import argparse
import csv
import datetime
import json
import os
import shutil
import sys
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def human_size(num_bytes: int) -> str:
    """Formats bytes into human-readable representation."""
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if num_bytes < 1024.0 or unit == "TB":
            return f"{num_bytes:.2f} {unit}" if unit != "B" else f"{num_bytes} B"
        num_bytes /= 1024.0
    return f"{num_bytes:.2f} TB"


def classify_file(path_str: str, ext: str, size: int) -> Tuple[str, str]:
    """
    Classifies file into robotics & V-JEPA research domains.
    Returns (category, description).
    """
    p_lower = path_str.lower()
    ext_lower = ext.lower()

    # 1. Perception & Object Detection
    if any(k in p_lower for k in ["yolo", "roboflow", "jarvis_object_detection"]):
        if ext_lower in [".pt", ".pth", ".onnx", ".engine"]:
            return ("PERCEPTION_WEIGHTS", "YOLO / Visual Detector Model Checkpoint")
        if ext_lower in [".yaml", ".yml", ".txt"]:
            return ("PERCEPTION_CONFIG", "YOLO Dataset Annotation / Config")
        if ext_lower in [".jpg", ".jpeg", ".png"]:
            return ("PERCEPTION_IMAGE", "Labeled Object Detection Image")

    # 2. V-JEPA & Vision Trajectories
    if ext_lower in [".mp4", ".avi", ".mkv", ".webm"] or ("wrist" in p_lower and ext_lower in [".mp4", ".png", ".jpg"]):
        return ("VJEPA_VISION_VIDEO", "Video Sequence / Camera Stream for Visual World Modeling")
    if "depth" in p_lower and ext_lower in [".png", ".npy", ".npz"]:
        return ("VJEPA_DEPTH_STREAM", "16-bit Depth Observation Frame")

    # 3. Piper Robot Telemetry & Actions
    if any(k in p_lower for k in ["trajectory", "stream_journal", "qpos", "action", "joint"]):
        if ext_lower in [".json", ".jsonl", ".csv"]:
            return ("PIPER_TELEMETRY", "Synchronized Robot Joint & Action Telemetry Log")
        if ext_lower in [".hdf5", ".h5", ".npz"]:
            return ("PIPER_DATASET_HDF5", "ALOHA/ACT/LeRobot Formatted Episode Array")

    # 4. ROS Bags & MCAP
    if ext_lower in [".mcap", ".db3"] or "metadata.yaml" in p_lower:
        return ("ROS_BAG_MCAP", "ROS 2 Native MCAP / SQLite Bag Recording")

    # 5. Pika Sense & Teleoperation
    if any(k in p_lower for k in ["pika", "teleop", "vive", "survive", "openvr"]):
        if ext_lower in [".rules", ".json", ".conf", ".yaml"]:
            return ("PIKA_TELEOP_CONFIG", "Pika Sense / SteamVR Teleoperation Tracking Config")
        if ext_lower in [".md", ".pdf", ".txt"]:
            return ("PIKA_DOCUMENTATION", "Pika Sense & Hardware User Guide / Calibration Spec")

    # 6. Robot Description & MoveIt
    if ext_lower in [".urdf", ".xacro"]:
        return ("ROBOT_URDF", "Kinematic Robot Model Description (URDF/Xacro)")
    if ext_lower == ".srdf":
        return ("MOVEIT_SRDF", "MoveIt 2 Semantic Robot Description & Collision Matrix")
    if ext_lower in [".stl", ".step", ".3mf", ".f3d", ".dae"]:
        return ("ROBOT_CAD_MESH", "3D CAD Model / Mesh Asset")

    # 7. Model Checkpoints & Exports
    if ext_lower in [".pt", ".pth", ".onnx", ".torchscript", ".safetensors", ".ckpt"]:
        return ("LEARNING_CHECKPOINT", "Imitation / RL / World Model Neural Network Weights")

    # 8. ROS 2 & Project Code
    if "launch" in p_lower and ext_lower in [".py", ".xml"]:
        return ("ROS_LAUNCH_FILE", "ROS 2 System Launch Pipeline")
    if ext_lower == ".py":
        return ("PYTHON_SOURCE", "Robotics System Source Code")
    if ext_lower == ".sh":
        return ("SHELL_SCRIPT", "Automation / Bringup / Diagnostic Script")
    if ext_lower in [".yaml", ".yml", ".toml"]:
        return ("SYSTEM_CONFIG", "ROS 2 / MoveIt / Package Configuration")

    # 9. Diagnostics & Logs
    if ext_lower in [".log", ".out"] or "test_output" in p_lower:
        return ("DIAGNOSTICS_LOG", "Execution Telemetry & Benchmark Test Output")
    if ext_lower in [".md", ".docx", ".pdf"]:
        return ("DOCUMENTATION", "Engineering Spec / Operation Manual / Benchmark Report")
    if ext_lower == ".zip":
        return ("ARCHIVE_DATA", "Compressed Project / Dataset / Benchmark Archive")

    return ("MISC_FILE", "Uncategorized Workspace File")


def discover_candidate_directories() -> List[str]:
    """Finds candidate project folders across Windows and WSL filesystems."""
    candidates = []

    # Windows project paths
    win_paths = [
        r"D:\yaswanth\ranger mini\jarvis-piper",
        r"D:\yaswanth\ranger mini\jarvis_piper_ws",
        r"D:\yaswanth\ranger mini\Jarvis_Object_Detection.v1i.yolov11",
        r"D:\yaswanth\ranger mini\sensor_workbench_ws",
        r"D:\yaswanth\lerobot",
        r"D:\yaswanth\ROBOTIC ARM",
        r"D:\yaswanth\ranger mini",
    ]

    # WSL paths via UNC network share
    wsl_paths = [
        r"\\wsl.localhost\Ubuntu-26.04\home\yash\ranger_mini_lyrical_2604_ws",
        r"\\wsl.localhost\Ubuntu-26.04\home\yash\ranger_mini_lyrical_2604_project",
        r"\\wsl.localhost\Ubuntu-22.04\home\yash\pika_ros",
        r"\\wsl.localhost\Ubuntu-22.04\home\yash\robotics_platform",
        r"\\wsl.localhost\Ubuntu-22.04\home\yash\ranger_mini_lyrical_ws",
        r"\\wsl.localhost\Ubuntu-22.04\home\yash\open_manipulator",
        r"\\wsl.localhost\Ubuntu-22.04\home\yash\ranger_sdk_ws",
    ]

    # If running natively in Linux/WSL
    linux_paths = [
        os.path.expanduser("~/pika_ros"),
        os.path.expanduser("~/data"),
        os.path.expanduser("~/database"),
        os.path.expanduser("~/benchmark"),
        os.path.expanduser("~/record_mcap_node"),
        os.path.expanduser("~/compress_camera_node"),
        os.path.expanduser("~/compress_camera_node2"),
        os.path.expanduser("~/ranger_mini_lyrical_2604_ws"),
        os.path.expanduser("~/ranger_mini_lyrical_2604_project"),
        "/mnt/d/yaswanth/ranger mini/jarvis-piper",
        "/mnt/d/yaswanth/ranger mini/Jarvis_Object_Detection.v1i.yolov11",
    ]

    all_potential = win_paths + wsl_paths + linux_paths
    for p in all_potential:
        if os.path.exists(p) and p not in candidates:
            candidates.append(os.path.abspath(p))

    return candidates


def scan_workspace(
    target_dirs: List[str],
    max_depth: int = 5,
    max_scan_files_per_dir: int = 500,
) -> List[Dict[str, Any]]:
    """
    Recursively scans target directories for relevant data, models, and code.
    Ignores heavy virtualenvs, git internals, and build caches.
    """
    ignore_dirs = {
        ".git", ".cache", "__pycache__", ".vscode", "venv", ".venv",
        "node_modules", "CMakeFiles", "dist", "egg-info", "CMakeTmp"
    }

    relevant_extensions = {
        ".mp4", ".avi", ".mkv", ".png", ".jpg", ".jpeg",
        ".mcap", ".db3", ".bag", ".h5", ".hdf5", ".npz",
        ".json", ".jsonl", ".csv", ".yaml", ".yml",
        ".pt", ".pth", ".onnx", ".torchscript", ".engine", ".safetensors",
        ".urdf", ".xacro", ".srdf", ".stl", ".step",
        ".py", ".sh", ".rules", ".log", ".txt", ".md", ".zip"
    }

    inventory = []
    scanned_paths = set()

    for base_dir in target_dirs:
        if not os.path.isdir(base_dir):
            continue

        base_path = Path(base_dir)
        count_in_dir = 0

        for root, dirs, files in os.walk(base_dir):
            # Prune ignored directories
            dirs[:] = [d for d in dirs if d not in ignore_dirs and not d.startswith(".")]

            # Check relative depth
            rel_depth = len(Path(root).relative_to(base_path).parts)
            if rel_depth > max_depth:
                dirs.clear()
                continue

            for fname in files:
                ext = os.path.splitext(fname)[1].lower()
                if ext not in relevant_extensions:
                    continue

                full_path = os.path.abspath(os.path.join(root, fname))
                if full_path in scanned_paths:
                    continue
                scanned_paths.add(full_path)

                try:
                    stat = os.stat(full_path)
                    f_size = stat.st_size
                    f_mtime = datetime.datetime.fromtimestamp(stat.st_mtime).isoformat()
                except Exception:
                    continue

                category, desc = classify_file(full_path, ext, f_size)

                inventory.append({
                    "relative_or_full_path": full_path,
                    "filename": fname,
                    "category": category,
                    "extension": ext,
                    "size_bytes": f_size,
                    "size_human": human_size(f_size),
                    "modified_time": f_mtime,
                    "description": desc,
                    "source_root": base_dir,
                })

                count_in_dir += 1
                if count_in_dir >= max_scan_files_per_dir:
                    break

    return inventory


def run_collection(
    inventory: List[Dict[str, Any]],
    output_dir: str,
    max_copy_size_mb: int = 50,
) -> Dict[str, Any]:
    """
    Copies relevant files into structured collection directory.
    Caps large files above threshold to protect disk space.
    """
    os.makedirs(output_dir, exist_ok=True)
    max_bytes = max_copy_size_mb * 1024 * 1024

    stats = {
        "total_files": len(inventory),
        "copied_count": 0,
        "skipped_size_count": 0,
        "categories": {},
    }

    for item in inventory:
        cat = item["category"]
        stats["categories"][cat] = stats["categories"].get(cat, 0) + 1

        target_sub = os.path.join(output_dir, cat.lower())
        os.makedirs(target_sub, exist_ok=True)

        src = item["relative_or_full_path"]
        dst = os.path.join(target_sub, item["filename"])

        # Avoid name collision
        if os.path.exists(dst):
            stem, ext = os.path.splitext(item["filename"])
            dst = os.path.join(target_sub, f"{stem}_{len(item['filename'])}{ext}")

        if item["size_bytes"] <= max_bytes:
            try:
                shutil.copy2(src, dst)
                stats["copied_count"] += 1
            except Exception:
                pass
        else:
            stats["skipped_size_count"] += 1

    return stats


def main():
    parser = argparse.ArgumentParser(
        description="Comprehensive Piper + Pika + ROS 2 + V-JEPA Workspace Data Collection & Inventory Tool"
    )
    parser.add_argument(
        "--inventory-only",
        action="store_true",
        help="Generate inventory CSV and report without copying files",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Custom output directory (default: workspace_data_collection_<timestamp>)",
    )
    parser.add_argument(
        "--max-file-mb",
        type=int,
        default=50,
        help="Maximum individual file size in MB to copy (default: 50 MB)",
    )
    args = parser.parse_args()

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = args.output_dir or f"workspace_data_collection_{timestamp}"

    print("=" * 80)
    print("      JARVIS-PiPER: WORKSPACE FORENSIC DATA INVENTORY & COLLECTION")
    print("=" * 80)

    candidate_dirs = discover_candidate_directories()
    print(f" Discovered {len(candidate_dirs)} candidate project search roots:")
    for d in candidate_dirs:
        print(f"   • {d}")

    print("\n Scanning directories for robotics telemetry, visual streams, models, and code...")
    inventory = scan_workspace(candidate_dirs)
    print(f" [OK] Identified {len(inventory)} relevant project and data files.\n")

    # Output inventory CSV
    os.makedirs(out_dir, exist_ok=True)
    csv_path = os.path.join(out_dir, "inventory.csv")

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        fieldnames = [
            "path", "filename", "category", "extension",
            "size_bytes", "size_human", "modified_time", "description"
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for item in inventory:
            writer.writerow({
                "path": item["relative_or_full_path"],
                "filename": item["filename"],
                "category": item["category"],
                "extension": item["extension"],
                "size_bytes": item["size_bytes"],
                "size_human": item["size_human"],
                "modified_time": item["modified_time"],
                "description": item["description"],
            })

    print(f" >>> Inventory CSV written to: {csv_path}")

    # Domain summary
    cat_summary = {}
    for item in inventory:
        cat = item["category"]
        cat_summary[cat] = cat_summary.get(cat, 0) + 1

    print("\n" + "=" * 80)
    print("                    DATASET INVENTORY CATEGORY SUMMARY")
    print("=" * 80)
    print(f" {'Category':<26} | {'Count':<7} | {'Domain Description':<40}")
    print("-" * 80)
    for cat, count in sorted(cat_summary.items(), key=lambda x: -x[1]):
        desc = next(x["description"] for x in inventory if x["category"] == cat)
        print(f" {cat:<26} | {count:<7} | {desc:<40}")
    print("=" * 80)

    if args.inventory_only:
        print("\n [INVENTORY COMPLETE] Ran with --inventory-only. Zero files were copied.")
        return 0

    print(f"\n Collecting and copying files into: {out_dir} (capped at {args.max_file_mb} MB/file)...")
    stats = run_collection(inventory, out_dir, max_copy_size_mb=args.max_file_mb)
    print(f" [COPY COMPLETE] {stats['copied_count']} files copied | {stats['skipped_size_count']} large files referenced in CSV.")

    # Generate summary JSON
    summary_path = os.path.join(out_dir, "collection_summary.json")
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump({
            "timestamp": timestamp,
            "total_files_indexed": len(inventory),
            "files_copied": stats["copied_count"],
            "files_skipped_due_to_size": stats["skipped_size_count"],
            "category_counts": cat_summary,
            "search_roots": candidate_dirs,
        }, f, indent=2)

    print(f" >>> Collection summary saved to: {summary_path}")
    print("=" * 80)
    return 0


if __name__ == "__main__":
    sys.exit(main())
