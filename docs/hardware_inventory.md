# JARVIS-PiPER: Hardware Inventory & Compatibility Matrix

**Target System:** Single-Arm JARVIS Manipulation Workcell  
**Status Date:** October 2026  
**Policy:** Strict Hardware Isolation (Zero Silent Fallbacks)

---

## 1. Discovered Equipment Matrix

| Device Name | Role in Workcell | Interface / Bus | Identifiers / Drivers | Verification Status | Operational Notes |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **AgileX PiPER Arm 1** | Primary 6-DOF Manipulator | SocketCAN (`can0`) / 1 Mbps | Firmware S-V1.6-3+, `piper_msgs` | **ACTIVE TARGET** | Single arm under test; 6 revolute joints, 1.5kg payload. |
| **AgileX PiPER Arm 2** | Secondary Arm (Future Dual-Arm) | SocketCAN (`can1`) / 1 Mbps | Not plugged | **NOT CONNECTED** | Marked `BLOCKED_HARDWARE`. Code architecture supports `arm_id=2`. |
| **Auxiliary Arm 3** | Third Arm (Nero / SO-100) | USB Serial / CAN | `nero_description` in WS | **NOT CONNECTED** | Marked `BLOCKED_HARDWARE`. Separate adapter interface reserved. |
| **PiPER Parallel Gripper** | End-Effector Tool | CAN / Type-C USB 3.0 | Stroke: 0 to 35 mm, $20\,\text{N}$ max grip | **ACTIVE TARGET** | Tested in simulation and action server interface. |
| **PIKA Sense Device** | 6-DOF Spatial Teleoperator | SteamVR 2.4GHz Wireless | USB VID `0x28de`, udev `81-vive.rules` | **STANDBY** | Requires wireless USB receiver plugged in for teleoperation. |
| **PIKA Station** | IR Lighthouse Tracking Station | 12V DC Wall Power | HTC Vive Lighthouse v2.0 Protocol | **STANDBY** | Requires line-of-sight to PIKA Sense photodiodes. |
| **Perception Camera** | Scene & Workspace RGB-D | USB 3.0 SuperSpeed | Intel RealSense D435/D455, `librealsense` | **ACTIVE TARGET** | Topic `/camera/color/image_raw`, `/camera/depth/image_rect`. |
| **Host Workstation** | Computation, ROS 2, AI Inference | PCI-e / Internal Bus | RTX 5060 Laptop GPU (8GB), Driver 591.86 | **CONFIRMED** | Supports Isaac Sim, YOLO11, and PyTorch inference. |

---

## 2. Piper Arm 1 Joint Limits & Actuator Parameters

| Joint Name | Joint Axis | Coordinate Range [rad] | Velocity Limit [rad/s] | Peak Torque [Nm] | Physical Description |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `piper_joint1` | Yaw ($Z$) | $[-2.618, +2.618]$ | $3.14$ | $30.0$ | Base rotation |
| `piper_joint2` | Pitch ($Y$) | $[0.000, +3.141]$ | $3.14$ | $30.0$ | Shoulder joint |
| `piper_joint3` | Pitch ($Y$) | $[-2.967, 0.000]$ | $3.14$ | $18.0$ | Elbow joint |
| `piper_joint4` | Roll ($X$) | $[-1.745, +1.745]$ | $3.14$ | $18.0$ | Forearm twist |
| `piper_joint5` | Pitch ($Y$) | $[-1.222, +1.222]$ | $3.14$ | $10.0$ | Wrist bend |
| `piper_joint6` | Roll ($Z$) | $[-2.094, +2.094]$ | $3.14$ | $10.0$ | Wrist tool rotation |
| `piper_finger_left_joint` | Prismatic ($X$) | $[0.000, 0.035]\,\text{m}$ | $0.05\,\text{m/s}$ | $20.0\,\text{N}$ | Parallel claw |

---

## 3. Communication & Port Mapping

```
[Physical Host]
  ├─ USB 3.0 Port A ──> Intel RealSense D435 / D455 Camera
  ├─ USB 3.0 Port B ──> USB-to-CAN Adapter (CANable / Candlelight) ──> Piper Arm 1 CAN Port (1 Mbps)
  ├─ USB 2.0 Port C ──> SteamVR Wireless Receiver (VID 0x28de) <──> PIKA Sense (2.4 GHz)
  └─ USB Type-C Port ─> PIKA Gripper Direct Diagnostic / USB Interface (if used standalone)
```

---

## 4. Hardware Verification Protocols

1. **Physical SocketCAN Verification:**
   ```bash
   # When USB-to-CAN adapter is plugged in:
   dmesg | grep -i can
   sudo ip link set can0 up type can bitrate 1000000
   ip -s link show can0
   ```
2. **SteamVR Receiver Verification:**
   ```bash
   lsusb -d 28de:
   ```
3. **Camera Pipeline Verification:**
   ```bash
   realsense-viewer  # or ros2 launch realsense2_camera rs_launch.py
   ```
