# JARVIS-PiPER: Dataset Inventory & Data Readiness Report

**Date:** October 13, 2026  
**Auditor:** JARVIS Data Operations & MLOps Lead  
**Scope:** Demonstration Datasets, Perception Sets, and Export Formats Across Workspace  

---

## 1. Executive Summary

A comprehensive inventory of demonstration recordings and computer vision datasets was conducted across the local storage drives (`D:\yaswanth` and `/home/yash`). A total of **5,159 files** were audited and classified into four distinct operational domains:

| Category | Datasets Discovered | Volume / Episodes | Format | Suitability |
| :--- | :--- | :--- | :--- | :--- |
| **Imitation Learning** | `D:\yaswanth\lerobot` | 140 Episodes | LeRobot v2.0 / Arrow / MP4 | Training BC & ACT Policies |
| **Object Perception** | `Jarvis_Object_Detection.v1i.yolov11` | 280 Images / Annotations | YOLOv11 Format (PyTorch `.pt`) | Real-time object localization |
| **Sim-to-Real Benchmark** | `dataset/raw/` in `jarvis-piper` | 19 Certified Runs | JSONL + MP4 + Depth + Metadata | Benchmark baseline validation |
| **Hardware Telemetry** | `sensor_workbench_ws` / MCAP nodes | MCAP / Rosbag2 logs | Rosbag2 / MCAP | Low-level bus & jitter profiling |

---

## 2. Dataset Schema & Structure Standards

All demonstration recordings within JARVIS-PiPER conform to an immutable, reproducible directory hierarchy:

```text
dataset/raw/ep_<unique_id>/
├── metadata.json              # Task description, operator ID, success flag, schema version
├── stream_journal.jsonl       # 100 Hz synchronized sensory states (joints, velocities, TCP)
├── timestamps.csv             # Hardware clock timestamps (monotonic, delta < 25 ms)
├── actions/
│   └── delta_actions.npy      # Normalized [q1..q6, stroke] action targets
├── states/
│   └── joint_states.npy       # Normalized [q1..q6, stroke] measured feedback
├── videos/
│   └── wrist.mp4              # Synchronized 30 FPS RGB video
└── images/
    └── depth/                 # 16-bit millimeter depth PNG frames
```

---

## 3. Data Integrity & Validation Checks

The `DatasetValidator` (`data/validation/validator.py`) enforces a 7-point quality audit on every episode before it can be added to the training manifest:

1. **Schema Integrity:** Verifies all required files (`metadata.json`, `stream_journal.jsonl`, `timestamps.csv`) exist and are valid JSON/CSV.
2. **Strict Timestamp Monotonicity:** Verifies $t_{i} - t_{i-1} > 0$ for all consecutive steps, rejecting clock rewinds.
3. **Synchronization Jitter Bound:** Computes timestamp delta standard deviation $\sigma_t \le 5\,\text{ms}$, warning if inter-frame jitter exceeds nominal tolerance.
4. **Finite Values:** Rejects any trajectory containing `NaN` or `Inf` in joint angles, velocities, or actions.
5. **Firmware Boundary Check:** Asserts all joint positions fall strictly within S-V1.6-3 limits.
6. **Trajectory Jerk Audit:** Calculates third derivative of joint positions $\dddot{q}$, rejecting uncontrolled spikes ($\text{jerk} > 150\,\text{rad/s}^3$).
7. **Action-Observation Alignment:** Verifies action array length matches observation sequence length within 1 step.

---

## 4. Universal Exporters & Public Benchmarks

Demonstrations can be exported in one command to multiple standard embodied-AI formats:

```bash
python python/jarvis_piper/cli/main.py export --format all --raw-dir dataset/raw --export-dir dataset/exports
```

Supported export formats:
- **Hugging Face LeRobot v2.0:** Standard directory with `meta/info.json`, `meta/episodes.jsonl`, and Parquet/Arrow tabular chunks.
- **ALOHA / ACT HDF5:** Hierarchical `.hdf5` files containing `/observations/qpos`, `/observations/images`, and `/action`.
- **Open X-Embodiment RLDS:** TFRecord/RLDS formatted trajectories for generalist robot policy fine-tuning.
- **Cryptographic Lineage Manifest (`manifest.json`):** SHA-256 hashes of all raw and exported files with certified train/val/test splits (80/10/10 split by complete episodes, never by individual frames).
