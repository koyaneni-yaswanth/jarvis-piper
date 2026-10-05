# AgileX PiPER 6-DOF Robotic Arm

The **PiPER** is an open-architecture, 6-degree-of-freedom robotic manipulator designed for dexterous manipulation and imitation learning data collection.

---

## 1. Kinematics & Joint Conventions

The PiPER arm utilizes 6 revolute joints configured in an anthropomorphic serial chain:

| Joint Index | Joint Name | Type | Range (Rad) | Max Velocity (rad/s) |
|---|---|---|---|---|
| Joint 1 | `piper_joint1` | Revolute (Base Yaw) | $[-2.618, +2.618]$ | $2.5$ |
| Joint 2 | `piper_joint2` | Revolute (Shoulder Pitch) | $[0.0, +3.1415]$ | $2.5$ |
| Joint 3 | `piper_joint3` | Revolute (Elbow Pitch) | $[-2.967, 0.0]$ | $2.5$ |
| Joint 4 | `piper_joint4` | Revolute (Wrist Roll) | $[-1.745, +1.745]$ | $3.0$ |
| Joint 5 | `piper_joint5` | Revolute (Wrist Pitch) | $[-1.221, +1.221]$ | $3.0$ |
| Joint 6 | `piper_joint6` | Revolute (Tool Roll) | $[-3.1415, +3.1415]$ | $3.0$ |

---

## 2. Telemetry and Feedback Topics

| Signal | Topic | Type | Rate |
|---|---|---|---|
| Joint States (Pos, Vel, Effort) | `/piper/joint_states` | `sensor_msgs/msg/JointState` | 50 Hz |
| End-Effector Cartesian Pose | `/piper/tcp_pose` | `geometry_msgs/msg/PoseStamped` | 50 Hz |
| Follower Command Feedback | `/piper_teleop/joint_states` | `sensor_msgs/msg/JointState` | 50 Hz |

---

## 3. Forward Kinematics (FK)

JARVIS-PiPER provides built-in SE(3) forward kinematics in `python/world_model/spatial.py` computing link frames:
- `base_link` $\rightarrow$ `link1` $\rightarrow \dots \rightarrow$ `link6` $\rightarrow$ `tcp_link`.
- Generates 3D Cartesian trajectories without requiring MoveIt or heavy external dependencies.
