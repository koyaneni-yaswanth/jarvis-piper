#!/usr/bin/env python3
"""
JARVIS-PiPER: Dataset Inspector CLI.
Inspects raw MCAP and converted HDF5 demonstration episodes without altering data.

Usage:
    python tools/dataset_inspect.py /home/humble/pika_mgat_files/hdf5/episode_0003.hdf5
    python tools/dataset_inspect.py /home/humble/pika_mgat_files/episodes/episode_0003.mcap
"""

import sys
import os
import argparse
from pathlib import Path
import numpy as np


def inspect_hdf5(file_path: Path):
    import h5py

    print(f"\n================================================================================")
    print(f"HDF5 DATASET INSPECTION: {file_path.name}")
    print(f"Path: {file_path.resolve()}")
    print(f"Size: {file_path.stat().st_size / (1024 * 1024):.2f} MB")
    print(f"================================================================================\n")

    with h5py.File(file_path, "r") as f:
        print("--- 1. DATASET ARRAYS & GROUPS ---")
        def visitor(name, obj):
            if isinstance(obj, h5py.Dataset):
                enc = obj.attrs.get("encoding", "")
                enc_str = f" [{enc}]" if enc else ""
                print(f"  /{name:<36} shape={str(obj.shape):<18} dtype={str(obj.dtype):<10}{enc_str}")
        f.visititems(visitor)

        print("\n--- 2. ROOT ATTRIBUTES ---")
        for k, v in f.attrs.items():
            val_str = str(v)
            if len(val_str) > 80:
                val_str = val_str[:77] + "..."
            print(f"  {k:<24}: {val_str}")

        # Metrics check
        if "timestamps" in f and "observations/qpos" in f and "action" in f:
            t = f["timestamps"][:]
            qpos = f["observations/qpos"][:]
            action = f["action"][:]
            T = len(t)
            dur = t[-1] - t[0] if T > 1 else 0.0
            dt = np.diff(t)
            mean_dt = float(np.mean(dt)) if len(dt) > 0 else 0.0
            jitter = float(np.std(dt) * 1000.0) if len(dt) > 0 else 0.0

            print(f"\n--- 3. TIMING & FREQUENCY ---")
            print(f"  Total Frames      : {T}")
            print(f"  Total Duration    : {dur:.2f} s")
            print(f"  Mean Frame Rate   : {1.0 / mean_dt:.2f} Hz (dt = {mean_dt * 1000.0:.2f} ms)")
            print(f"  Timestamp Jitter  : {jitter:.2f} ms")

            print(f"\n--- 4. STATE & ACTION SPANS ---")
            names = ["x", "y", "z", "qx", "qy", "qz", "qw", "gripper"]
            for i in range(min(qpos.shape[1], len(names))):
                col = qpos[:, i]
                print(f"  qpos[{names[i]:<7}] : [{col.min():+8.3f} .. {col.max():+8.3f}]  span={np.ptp(col):.3f}")

            # Quaternion check
            if qpos.shape[1] >= 7:
                q_norms = np.linalg.norm(qpos[:, 3:7], axis=1)
                max_dev = float(np.max(np.abs(q_norms - 1.0)))
                print(f"  Quaternion Norm   : min={q_norms.min():.4f}, max={q_norms.max():.4f} (deviation={max_dev:.2e})")

            # Action shift check
            if len(action) == len(qpos):
                shift_err = float(np.max(np.abs(action[:-1] - qpos[1:])))
                print(f"  Action Alignment  : max |action[t] - qpos[t+1]| = {shift_err:.2e} "
                      f"{'[CORRECT 1-STEP FORWARD]' if shift_err < 1e-5 else '[MISALIGNED]'}")


def inspect_mcap(file_path: Path):
    try:
        from mcap.reader import make_reader
    except ImportError:
        print("[ERROR] 'mcap' package is required to inspect MCAP files.")
        print("        Install via pip or activate an environment with mcap.")
        sys.exit(1)

    print(f"\n================================================================================")
    print(f"MCAP RAW RECORDING INSPECTION: {file_path.name}")
    print(f"Path: {file_path.resolve()}")
    print(f"Size: {file_path.stat().st_size / (1024 * 1024):.2f} MB")
    print(f"================================================================================\n")

    topic_counts = {}
    timestamps = {}

    with open(file_path, "rb") as f:
        reader = make_reader(f)
        for schema, channel, message in reader.iter_messages():
            topic = channel.topic
            topic_counts[topic] = topic_counts.get(topic, 0) + 1
            if topic not in timestamps:
                timestamps[topic] = [message.log_time, message.log_time]
            else:
                timestamps[topic][1] = message.log_time

    print("--- 1. TOPIC MESSAGE COUNTS & RATES ---")
    for topic, count in sorted(topic_counts.items()):
        t_start, t_end = timestamps[topic]
        dur = (t_end - t_start) / 1e9
        rate = count / dur if dur > 0 else 0.0
        print(f"  {topic:<34} msgs={count:>6}   dur={dur:>6.2f}s   rate={rate:>6.1f} Hz")


def main():
    parser = argparse.ArgumentParser(description="JARVIS-PiPER Dataset Inspector")
    parser.add_argument("file_path", type=str, help="Path to HDF5 or MCAP file to inspect")
    args = parser.parse_args()

    path = Path(args.file_path)
    if not path.is_file():
        print(f"[ERROR] File does not exist: {path}")
        sys.exit(1)

    if path.suffix in [".h5", ".hdf5"]:
        inspect_hdf5(path)
    elif path.suffix == ".mcap":
        inspect_mcap(path)
    else:
        print(f"[ERROR] Unsupported file extension: {path.suffix}. Expected .hdf5, .h5, or .mcap")
        sys.exit(1)


if __name__ == "__main__":
    main()
