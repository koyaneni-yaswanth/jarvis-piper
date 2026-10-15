# JARVIS-PiPER: ROS 2 Interfaces & Coordinate Frames Specification

**Date:** October 15, 2026  
**Auditor:** JARVIS Systems Architecture Lead  
**Scope:** Vendor (`piper_ros`, `pika_ros`) and Native (`jarvis_piper_interfaces`) ROS 2 Ecosystem

---

## 1. PiPER Arm ROS 2 Interfaces (`piper_ros`)

Sourced from `/home/humble/piper_ros/install/setup.bash`.

### 1.1 `piper_msgs/msg/PosCmd`
Cartesian end-effector command interface.
```text
float64 x        # Flange X position (meters or scaled units)
float64 y        # Flange Y position (meters or scaled units)
float64 z        # Flange Z position (meters or scaled units)
float64 roll     # Flange Roll (radians)
float64 pitch    # Flange Pitch (radians)
float64 yaw      # Flange Yaw (radians)
float64 gripper  # Gripper stroke command
int32 mode1      # Control mode flag
int32 mode2      # Sub-mode flag
```

### 1.2 `piper_msgs/msg/PiperStatusMsg`
Low-level feedback status published by the CAN node.
```text
uint8 ctrl_mode
uint8 arm_status
uint8 mode_feedback
uint8 teach_status
uint8 motion_status
uint8 trajectory_num
int64 err_code
bool joint_1_angle_limit
bool joint_2_angle_limit
bool joint_3_angle_limit
bool joint_4_angle_limit
bool joint_5_angle_limit
bool joint_6_angle_limit
bool communication_status_joint_1
bool communication_status_joint_2
bool communication_status_joint_3
bool communication_status_joint_4
bool communication_status_joint_5
bool communication_status_joint_6
```

### 1.3 `piper_msgs/srv/Enable`
Motor enable and safety interlock service.
```text
bool enable_request
---
bool enable_response
```

---

## 2. PIKA Teleoperation Interfaces (`pika_ros`)

Sourced from `/home/humble/pika_ros/install/setup.bash`.

### 2.1 `data_msgs/msg/Gripper`
Handheld trigger feedback and command status.
```text
std_msgs/Header header
float64 angle         # Raw encoder angular displacement
float64 distance      # Gripper stroke reading in mm / meters
float64 effort        # Gripper measured effort / current
float64 velocity      # Gripper speed
bool enable           # Actuation enabled flag
bool set_zero         # Calibration origin flag
bool error            # Hardware fault flag
float64 voltage       # Bus voltage
float64 driver_temp   # Electronics temperature
float64 motor_temp    # Motor coil temperature
float64 bus_current   # Electrical current
string status         # Status string (Operating, Standby, Fault)
```

### 2.2 `data_msgs/msg/Instruction`
Natural-language multimodal task conditioning message.
```text
std_msgs/Header header
string text                           # Task prompt (e.g. "pick up red block")
builtin_interfaces/Time start_stamp   # Voice/instruction start timestamp
builtin_interfaces/Time end_stamp     # Voice/instruction completion timestamp
```

### 2.3 Additional Teleop Messages
- `data_msgs/msg/LocalizationStatus`: `bool accurate` (optical tracking lock indicator)
- `data_msgs/msg/ArmControlStatus`: `bool over_limit` (workspace boundary check indicator)
- `data_msgs/msg/TeleopStatus`: Teleoperator state and clutch status

---

## 3. JARVIS-PiPER Production Interfaces (`jarvis_piper_interfaces`)

Located at `/home/humble/robotics/jarvis-piper/ros2_ws/src/jarvis_piper_interfaces`.

| Interface Name | Type | Key Fields / Payload |
| :--- | :--- | :--- |
| `SynchronizedFrame` | Message | RGB color image, depth image, fisheye image, joint states (6-DOF), gripper state, timestamps |
| `EpisodeMetadata` | Message | Episode ID, task string, success flag, start/end timestamps, frame count, hardware IDs |
| `PikaTeleopStatus` | Message | Tracking status, clutch engaged, pose freshness, latency ms |
| `QualityAuditResult`| Message | Missing timestamps count, jitter stats, jerk metric, quaternion validity |
| `StartEpisode` | Service | `string task_instruction` -> `bool success, string episode_id` |
| `StopEpisode` | Service | `bool mark_success` -> `bool success, uint32 recorded_frames` |
| `DiscardEpisode` | Service | `string reason` -> `bool discarded` |
| `ExportDataset` | Service | `string format (hdf5/lerobot)` -> `bool success, string export_path` |

---

## 4. Coordinate Frames & Transformations

1. **Tracker Frame (`pika_sense`):**
   - Convention: Standard FLU (Forward-Left-Up) at tracker grip center.
   - Quaternions: `[qx, qy, qz, qw]` stored and converted via `transforms3d` / `scipy.spatial.transform`.
2. **Robot Flange Frame (`piper_flange`):**
   - Convention: Z-forward along end-effector approach vector.
   - Flange-to-Gripper Offset: `[0.0, 0.0, 0.13, 0.0, 0.0, 0.0]` (130 mm tool offset along +Z).
3. **Camera Frame (`realsense_d405_optical`):**
   - Color & Depth streams aligned to optical center.
   - Depth unit scale: `0.0001 m/unit` (0.1 mm/unit) queried from device firmware.
