# JARVIS-PiPER: Hardware Inventory & Interface Specification Report

**Date:** October 13, 2026  
**Auditor:** JARVIS Hardware Validation & Robotics Safety Lead  
**Target:** Single AgileX PiPER 6-DOF Manipulator + PIKA Sense Hub  

---

## 1. Physical Manipulator: AgileX PiPER 6-DOF

### 1.1 Hardware Specifications
- **Arm Configuration:** **ONE PHYSICAL ARM** currently installed on the workstation.
- **Degrees of Freedom:** 6 revolute arm joints + 1 prismatic bilateral gripper.
- **Reach & Payload:**
  - Spherical reach radius: $626\,\text{mm}$
  - Nominal payload capacity: $1.5\,\text{kg}$
  - Total arm mass: $4.2\,\text{kg}$
  - Repeatability: $\pm 0.1\,\text{mm}$
- **Firmware Support:** S-V1.6-3+ firmware protocol.

### 1.2 Authoritative Joint Specifications & Limits

| Joint ID | Name | Coordinate Limits [rad] | Range [deg] | Max Velocity [rad/s] | Max Torque [Nm] | Zero-Position Semantics |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Joint 1** | `joint1` (Base Yaw) | $[-2.618, +2.618]$ | $[-150^\circ, +150^\circ]$ | $3.14$ | $30.0$ | Facing forward ($+x$) |
| **Joint 2** | `joint2` (Shoulder Pitch) | $[0.000, +3.141]$ | $[0^\circ, +180^\circ]$ | $3.14$ | $30.0$ | Upright vertical |
| **Joint 3** | `joint3` (Elbow Pitch) | $[-2.967, 0.000]$ | $[-170^\circ, 0^\circ]$ | $3.14$ | $18.0$ | Collinear with upper arm |
| **Joint 4** | `joint4` (Forearm Roll) | $[-1.745, +1.745]$ | $[-100^\circ, +100^\circ]$ | $3.14$ | $18.0$ | Palm facing down |
| **Joint 5** | `joint5` (Wrist Pitch) | $[-1.222, +1.222]$ | $[-70^\circ, +70^\circ]$ | $3.14$ | $10.0$ | Straight wrist |
| **Joint 6** | `joint6` (Wrist Roll) | $[-2.094, +2.094]$ | $[-120^\circ, +120^\circ]$ | $3.14$ | $10.0$ | Neutral tool roll |
| **Gripper** | `gripper_joint` | $[0.000, 0.035]\,\text{m}$ | $[0, 35]\,\text{mm}$ stroke | $0.05\,\text{m/s}$ | $20.0\,\text{N}$ | Fully closed ($0.0\,\text{m}$) |

### 1.3 Communication Bus & SocketCAN Topology
- **Physical Bus:** CAN 2.0B differential pair (`CAN_H`, `CAN_L`).
- **Bitrate:** **1,000,000 bps (1 Mbps)**.
- **Interface Name:** `can0` via USB-to-CAN adapter (e.g. CANable / Candlelight firmware).
- **SocketCAN Bringup Command:**
  ```bash
  sudo ip link set can0 up type can bitrate 1000000
  ```

### 1.4 Topic Contracts: Distinguishing Genuine Feedback from Commanded Targets
To ensure safety and prevent feedback loops, command and feedback topics are strictly separated:

| Purpose | ROS 2 Topic | Message Type | Frequency | Source / Authority |
| :--- | :--- | :--- | :--- | :--- |
| **Measured Joint Feedback** | `/piper/joint_states` | `sensor_msgs/msg/JointState` | $100\,\text{Hz}$ | **CAN Motor Encoders (Ground Truth)** |
| **Commanded Joint Targets** | `/piper/arm_controller/commands` | `std_msgs/msg/Float64MultiArray` | Up to $100\,\text{Hz}$ | Safety Supervisor / Policy Node |
| **Gripper Measured State** | `/piper/gripper/state` | `sensor_msgs/msg/JointState` | $50\,\text{Hz}$ | **Gripper Motor Encoder** |
| **Gripper Commanded Target** | `/piper/gripper/command` | `std_msgs/msg/Float64` | On change | Task Planner |
| **Emergency Stop State** | `/piper/safety/estop` | `std_msgs/msg/Bool` | Event-driven | Latched Safety Supervisor |

---

## 2. Teleoperation Interface: AgileX PIKA Sense

### 2.1 Hardware Identity & Protocols
- **Tracking System:** 6-DOF spatial optical tracker tracking Lighthouse sweeps.
- **Wireless Receiver:** Valve SteamVR dongle (USB VID `0x28de`, PID `0x2101`).
- **Udev Rule:** Required rule at `/etc/udev/rules.d/81-vive.rules`.

### 2.2 Control Semantics & Safety Interlocks
1. **Clutch Button (Button 1):** Operator dead-man clutch.
   - *Pressed:* Relative Cartesian translation $\Delta x, \Delta y, \Delta z$ and rotation $\Delta R$ of the human hand are mapped to robot end-effector displacement.
   - *Released:* Hand moves freely without issuing robot commands (allows clutching/repositioning).
2. **Emergency Stop (Button 2):** Instant hardware disengage.
   - If pressed or if SteamVR tracking signal is lost (stale $>25\,\text{ms}$), arm immediately halts with zero commanded velocity.
3. **Signal Conditioning:** Physiological tremor is attenuated via a 2nd-order Butterworth low-pass filter ($f_c = 12\,\text{Hz}$).

---

## 3. Perception Sensors & Calibration

### 3.1 RGB-D Camera Specifications
- **Sensor Type:** Intel RealSense D435 / DepthAI OAK-D.
- **Streams Provided:**
  - `/camera/color/image_raw` ($640 \times 480$ RGB, 30 FPS)
  - `/camera/depth/image_raw` ($640 \times 480$ 16-bit millimeter depth, 30 FPS)
  - `/camera/color/camera_info` (Pinhole intrinsics matrix $K$)
- **Pinhole Intrinsics Calibration (Nominal):**
  $$f_x = 385.0, \quad f_y = 385.0, \quad c_x = 160.0, \quad c_y = 120.0$$
- **Fine-Tuned YOLO11 Detector:**
  - Path: `Jarvis_Object_Detection.v1i.yolov11/yolo11n.pt`
  - Classes: `['bowl', 'cup', 'red block']`
  - Output: 3D bounding box centroid in camera coordinate frame.

---

## 4. Hardware Isolation & Safety Interlocks

### 4.1 Strict Operating Modes
To prevent physical accidents, the system enforces 4 mutually exclusive backends:
1. `MOCK`: High-fidelity synthetic telemetry for unit tests (zero hardware required).
2. `SIMULATION`: Isaac Sim / PyPhysX digital twin (default operating mode).
3. `REPLAY`: Passive trajectory playback without motor commands.
4. `HARDWARE`: Physical SocketCAN actuation.

### 4.2 Physical Commissioning Safety Interlock
The system will **NEVER** command the physical CAN interface by default. Physical motion requires:
1. `can0` interface up and verified.
2. Verified presence of operator at emergency stop switch.
3. Explicit runtime confirmation token passed to the safety supervisor:
   ```python
   safety_supervisor.authorize_physical_commissioning("OPERATOR_COMMISSIONING_CONFIRMED")
   ```
If the token is omitted, any call to hardware adapters raises `PermissionError` and reports `BLOCKED_HARDWARE`.
