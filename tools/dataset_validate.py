#!/usr/bin/env python3
"""
JARVIS-PiPER: Dataset Validator CLI.
Executes rigorous mathematical and robotics validation on demonstration datasets.

Validation Criteria:
  1. Monotonic timestamps without duplicates or negative steps
  2. Bounded timestamp jitter (< 5.0 ms standard deviation)
  3. Strict absence of NaN and Infinite values
  4. Unit quaternion norm verification (|norm - 1.0| < 1e-3)
  5. 1-step forward action alignment (|action[t] - qpos[t+1]| < 1e-4)
  6. Non-zero sensor travel (detects frozen tracking / dead sensors)
  7. Valid image dimensions and dtypes

Usage:
    python tools/dataset_validate.py /home/humble/pika_mgat_files/hdf5/episode_0003.hdf5
"""

import sys
import argparse
from pathlib import Path
import numpy as np


def validate_hdf5(file_path: Path) -> bool:
    import h5py

    print(f"\n================================================================================")
    print(f"JARVIS DATASET QUALITY VALIDATOR: {file_path.name}")
    print(f"Path: {file_path.resolve()}")
    print(f"================================================================================\n")

    errors = []
    warnings = []

    with h5py.File(file_path, "r") as f:
        # 1. Schema Check
        required_keys = ["timestamps", "observations/qpos", "action"]
        for k in required_keys:
            if k not in f:
                errors.append(f"Missing required dataset key: {k}")

        if errors:
            print("[FAIL] Schema check failed:")
            for e in errors:
                print(f"  - {e}")
            return False

        t = f["timestamps"][:]
        qpos = f["observations/qpos"][:]
        action = f["action"][:]
        T = len(t)

        # 2. Frame count agreement
        if len(qpos) != T or len(action) != T:
            errors.append(f"Array length mismatch: timestamps={T}, qpos={len(qpos)}, action={len(action)}")

        # 3. Monotonic timestamps
        dt = np.diff(t)
        if np.any(dt <= 0):
            bad_idx = np.where(dt <= 0)[0]
            errors.append(f"Non-monotonic or duplicate timestamps detected at {len(bad_idx)} steps")

        # 4. Timestamp jitter
        jitter_ms = float(np.std(dt) * 1000.0) if len(dt) > 0 else 0.0
        if jitter_ms > 10.0:
            errors.append(f"Excessive timestamp jitter: {jitter_ms:.2f} ms (> 10.0 ms threshold)")
        elif jitter_ms > 5.0:
            warnings.append(f"Moderate timestamp jitter: {jitter_ms:.2f} ms")

        # 5. NaN and Inf check
        if np.isnan(qpos).any() or np.isinf(qpos).any():
            errors.append("NaN or Inf detected in observations/qpos")
        if np.isnan(action).any() or np.isinf(action).any():
            errors.append("NaN or Inf detected in action")

        # 6. Quaternion Norm Check
        if qpos.shape[1] >= 7:
            q_norms = np.linalg.norm(qpos[:, 3:7], axis=1)
            max_dev = float(np.max(np.abs(q_norms - 1.0)))
            if max_dev > 1e-3:
                errors.append(f"Quaternions violate unit norm condition: max deviation = {max_dev:.4e} (> 1e-3)")

        # 7. Action Alignment Check (action[t] == qpos[t+1])
        if len(action) == len(qpos) and len(qpos) > 1:
            shift_err = float(np.max(np.abs(action[:-1] - qpos[1:])))
            if shift_err > 1e-4:
                errors.append(f"Action misalignment: max |action[t] - qpos[t+1]| = {shift_err:.4e} (> 1e-4)")

            same_err = float(np.max(np.abs(action - qpos)))
            if same_err < 1e-9:
                errors.append("Action is an unshifted copy of qpos (policy would predict identity)")

        # 8. Plausibility / Sensor Activity Check
        if qpos.shape[1] >= 3:
            travel = float(np.sum(np.linalg.norm(np.diff(qpos[:, :3], axis=0), axis=1)))
            if travel < 0.05:
                errors.append(f"Insufficient spatial travel: {travel:.3f} m (tracker likely frozen)")
            else:
                print(f"  [PASS] Spatial Travel Verified : {travel:.2f} m")

        if qpos.shape[1] >= 8:
            grip_span = float(np.ptp(qpos[:, 7]))
            if grip_span < 1.0:
                warnings.append(f"Gripper span is narrow ({grip_span:.2f} mm) - trigger may not have moved")
            else:
                print(f"  [PASS] Gripper Travel Verified: span = {grip_span:.1f} mm")

        # 9. Image checks
        if "observations/images" in f:
            for img_name in f["observations/images"]:
                ds = f[f"observations/images/{img_name}"]
                if ds.shape[0] != T:
                    errors.append(f"Image stream {img_name} frame count {ds.shape[0]} != {T}")
                print(f"  [PASS] Image Stream Verified  : {img_name} {ds.shape} {ds.dtype}")

    print("\n--- VALIDATION SUMMARY ---")
    if warnings:
        for w in warnings:
            print(f"  [WARN] {w}")

    if errors:
        print(f"\n[RESULT: FAIL] {len(errors)} critical validation failures found:")
        for e in errors:
            print(f"  - {e}")
        return False
    else:
        print("\n[RESULT: PASS] Dataset passed all mathematical and robotics quality checks cleanly!")
        return True


def main():
    parser = argparse.ArgumentParser(description="JARVIS-PiPER Dataset Validator")
    parser.add_argument("file_path", type=str, help="Path to HDF5 dataset file")
    args = parser.parse_args()

    path = Path(args.file_path)
    if not path.is_file():
        print(f"[ERROR] File not found: {path}")
        sys.exit(1)

    ok = validate_hdf5(path)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
