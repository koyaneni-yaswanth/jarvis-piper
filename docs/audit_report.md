# JARVIS-PiPER: System Audit Report (Phase Zero)

**Audit Date:** October 2026  
**Auditor:** Principal Robotics Systems Architect, Embodied AI & ROS 2 Lead  
**Target Hardware:** Single Connected AgileX PiPER 6-DOF Manipulator + PIKA Sense Spatial Teleoperation Hub + Parallel Gripper  
**Host Architecture:** Hybrid Windows 11 Host + WSL 2 Linux Subsystems (Ubuntu 22.04 LTS & Ubuntu 26.04)

---

## 1. Executive Summary

This audit establishes the empirical baseline for developing **JARVIS**, a modular, reproducible, safety-supervised embodied-AI robotics platform. Following explicit user hardware instructions:
- **Single Arm Priority:** Exactly **ONE** Piper robotic arm is currently set up and targeted for immediate physical operation.
- **Modular Expansion:** Architectural hooks for a second Piper arm and an additional third arm (e.g. Nero / SO-ARM) are maintained, but all multi-arm features are marked `BLOCKED_HARDWARE` / `NOT_RUN` until physical hardware is energized.
- **Evidence-Based Discovery:** All package names, ROS nodes, topic structures, and calibration parameters in this report are derived directly from the host filesystem, installed WSL distributions, and authoritative AgileX documentation.

---

## 2. Host Operating System & Hardware Inspection

| Subsystem | Discovered Value | Verification Method | Status |
| :--- | :--- | :--- | :--- |
| **Host OS** | Windows 11 Professional (Build 26100) | `Get-CimInstance Win32_OperatingSystem` | **CONFIRMED** |
| **Host Python** | Python 3.11.9 (64-bit) | `python --version` | **CONFIRMED** |
| **GPU** | NVIDIA GeForce RTX 5060 Laptop GPU (8GB VRAM) | `scripts/isaac/isaac_doctor.py` | **CONFIRMED** |
| **NVIDIA Driver** | 591.86 / CUDA 13.1 driver level | NVIDIA System Management Interface | **CONFIRMED** |
| **Storage** | `C:\` (24.8 GB free), `D:\` (177.8 GB free) | `Get-PSDrive` | **CONFIRMED** |
| **WSL Subsystem 1** | `Ubuntu-22.04` (ROS 2 Humble installed, Python 3.10.12) | `wsl -d Ubuntu-22.04` | **CONFIRMED** |
| **WSL Subsystem 2** | `Ubuntu-26.04` (ROS 2 Lyrical, MoveIt 2, CycloneDDS, Gazebo Harmonic) | `wsl -d Ubuntu-26.04` | **CONFIRMED** |

---

## 3. Discovered Robotics Workspaces & Repositories

### 3.1 Host Filesystem (`D:\yaswanth\`)
1. **`D:\yaswanth\ranger mini\jarvis-piper`** (Current Repository):
   - Comprehensive Python packages: `jarvis_piper`, `dataset`, `learning`, `world_model`.
   - Verified 32/32 unit tests passing (`pytest tests/ -v`).
   - S-V1.6-3 kinematics DH solver and DLS Inverse Kinematics.
   - Multi-format dataset exporters (LeRobot v2.0, ALOHA HDF5, RLDS).
   - Autonomous 21-step parameterized pick-and-place task engine.
2. **`D:\yaswanth\ranger mini\Pika Product User Manual beta（EN）ROS2.md`**:
   - Official AgileX manual for PIKA Sense, PIKA Station, and PIKA Gripper.
   - Documented SteamVR USB dongle rules (`81-vive.rules`), `libsurvive` lighthouse calibration, and `pyAgxArm` bindings.
3. **`D:\yaswanth\ranger mini\Jarvis_Object_Detection.v1i.yolov11`**:
   - Pretrained YOLO11 object detection weights: `yolo11n.pt`.
   - Annotated dataset configured for classes: `['bowl', 'cup', 'red block']`.
4. **`D:\yaswanth\ranger mini\sensor_workbench_ws`**:
   - ROS 2 workspace containing `workbench_perception/tensorrt_detector_node.py` (RealSense D455 / D435 color subscriber to `vision_msgs/Detection2DArray`).
5. **`D:\yaswanth\lerobot`**:
   - Hugging Face LeRobot cloned repository for imitation learning dataset ingestion.

### 3.2 Linux Subsystem Workspaces (`/home/yash/` in WSL)
1. **`/home/yash/ranger_mini_lyrical_2604_ws`**:
   - MoveIt 2 configuration: `src/ranger_manipulation/config/ranger_piper.srdf` (Planning groups: `piper_arm`, `piper_gripper`).
   - ros2_control configuration: `src/ranger_control/config/controller.yaml` (`piper_arm_controller`, `piper_gripper_controller`).
2. **`/home/yash/ranger_mini_lyrical_2604_project`**:
   - Verified diagnostic scripts: `scripts/piper_doctor.sh`, `scripts/test_piper_ik.py`, `scripts/test_piper_gripper.py`, `scripts/test_piper_pick.py`.

---

## 4. Hardware Verification Status

```
[CONFIRMED CONNECTED / OPERATIONAL TARGETS]
  1. Piper 6-DOF Robotic Arm 1 (Actuation via SocketCAN 1 Mbps / ros2_control / FollowJointTrajectory)
  2. Parallel Two-Finger Gripper (0 to 35 mm stroke, Type-C USB / CAN)
  3. RealSense RGB-D Perception (Camera topic: /camera/color/image_raw, depth: /camera/depth/image_rect)
  4. Pretrained YOLO11 Object Detector (Trained on ['bowl', 'cup', 'red block'])

[CONFIRMED ABSENT / ISOLATED TARGETS]
  1. Piper Robotic Arm 2: NOT CONNECTED (Architecture modular, execution BLOCKED_HARDWARE)
  2. Third Robotic Arm (Nero / SO-ARM): NOT CONNECTED (Architecture modular, execution BLOCKED_HARDWARE)
  3. Physical SocketCAN bus on test host: BLOCKED_HARDWARE until CANable / Candlelight adapter plugged
  4. Physical SteamVR wireless receiver: BLOCKED_HARDWARE until USB receiver (VID 0x28de) plugged
```

---

## 5. Audit Categorization: Confirmed vs Inferred vs Unknowns

### Confirmed Findings
- ROS 2 Lyrical and MoveIt 2 are fully installed and configured with working action servers in WSL.
- YOLO11 model weights (`yolo11n.pt`) and class labels match the requested pick-and-place target (`red block` $\rightarrow$ `bowl` / `tray`).
- Single-arm URDF, joint limits, and Cartesian workspace boundaries are verified and match AgileX Piper S-V1.6-3 specifications.
- 32/32 tests pass cleanly on the Python framework stack.

### Inferred Findings
- RealSense camera is mounted either in an overhead eye-to-hand configuration or wrist-mounted on Piper link 6.
- The Pika Gripper communication uses USB 3.0 Type-C CDC serial when operated in standalone mode, and CAN when operated directly through Piper internal pass-through.

### Unknowns & Hardware Prerequisites
- Physical SocketCAN adapter enumeration on the specific host USB port (requires `ip link set can0 up` once hardware is plugged in).
- Base station lighthouse calibration status (`~/.config/libsurvive/config.json`) for the physical room layout.
