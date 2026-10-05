# Universal Dataset Schema Specification

JARVIS-PiPER defines a canonical dataset representation designed to export effortlessly to LeRobot, ALOHA HDF5, RLDS, and PyTorch dataloaders.

---

## 1. Directory Structure

Each recorded episode occupies a self-contained directory under `dataset/raw/`:

```
dataset/raw/ep_demo_001_20261005_120000/
├── metadata.json           # Episode provenance, task, environment, duration
├── trajectory.json         # Full structured time-series state & action records
├── stream_journal.jsonl    # High-speed append-only stream log
├── camera_wrist.mp4        # Wrist camera MP4 (30 FPS, H.264)
├── camera_base.mp4         # Optional stationary camera MP4
└── images/                 # Keyframe snapshots
    ├── wrist/
    │   └── frame_000000.jpg
    └── depth/
        └── depth_000000.png
```

---

## 2. Metadata Schema (`metadata.json`)

```json
{
  "episode_id": "ep_demo_001_20261005_120000",
  "task_instruction": "Pick up the red cube and place in tray",
  "task_category": "pick_and_place",
  "operator_id": "human_operator_1",
  "source_label": "REAL_HARDWARE",
  "robot_platform": "PiPER_6DOF",
  "success_label": true,
  "duration_sec": 12.4,
  "total_steps": 620,
  "target_fps": 50.0,
  "start_timestamp": "2026-10-05T12:00:00.123456",
  "end_timestamp": "2026-10-05T12:00:12.523456",
  "schema_version": "2.0.0"
}
```

---

## 3. Step Schema (`stream_journal.jsonl` & `trajectory.json`)

Each timestep dictionary contains:

| Field | Type | Description |
|---|---|---|
| `step_index` | `int` | Monotonically increasing index ($0, 1, \dots, N-1$) |
| `timestamp` | `float` | Monotonic timestamp in seconds |
| `joint_positions` | `float[6]` | PiPER 6-DOF joint angles in radians |
| `joint_velocities`| `float[6]` | PiPER joint velocities in rad/s |
| `joint_efforts`   | `float[6]` | PiPER joint torque/effort in Nm |
| `gripper_stroke`  | `float` | Gripper opening width in meters ($0.0$ to $0.035$) |
| `tcp_pose.position` | `float[3]` | Tool Center Point $[x, y, z]$ in meters |
| `tcp_pose.orientation` | `float[4]` | Tool Center Point quaternion $[x, y, z, w]$ |
| `action` | `float[7]` | Target command vector ($q_{1..6}, stroke$) |
