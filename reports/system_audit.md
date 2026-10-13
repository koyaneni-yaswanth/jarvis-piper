# JARVIS Phase 0: System Audit Report

**Date of Audit:** October 13, 2026  
**Auditor:** JARVIS Embodied-AI & Robotics Systems Lead  
**Target Hardware:** ONE AgileX PiPER 6-DOF Manipulator with Parallel Gripper & PIKA Sense Teleoperation Hub  
**Host Architecture:** Hybrid Windows 11 Host + WSL2 Ubuntu Environments  

---

## 1. Host Compute & Acceleration Architecture

| Component | Specification / Version | Empirical Verification Method | Status |
| :--- | :--- | :--- | :---: |
| **Operating System** | Windows 11 Enterprise (Build 26100, AMD64) | `platform.platform()` | Verified |
| **CPU Architecture** | x86_64 / AMD64 Multicore Processor | Host Sysinfo | Verified |
| **GPU Model** | NVIDIA GeForce RTX 5060 Laptop/Desktop GPU | `nvidia-smi --query-gpu` | Verified |
| **NVIDIA Driver** | **591.86** (WDDM 3.2, requirement $\ge 535.129$) | `nvidia-smi` | Verified |
| **CUDA Driver API** | **13.1** (Compute Capability 9.0+) | `nvidia-smi` | Verified |
| **GPU Dedicated VRAM** | **8,151 MiB (8.0 GB)** | `nvidia-smi` | Verified |
| **Available Disk Space** | Drive `D:\`: $>180\,\text{GB}$ free; Drive `C:\`: $>120\,\text{GB}$ free | `Get-PSDrive` | Sufficient |

---

## 2. Operating System & Containerized Environments

The host system operates two isolated Windows Subsystem for Linux (WSL2) instances alongside the native Windows environment:

### 2.1 WSL2: Ubuntu 22.04.5 LTS (`jammy`)
- **Kernel:** Linux 6.6.x x86_64
- **Primary User:** `yash` (`/home/yash`)
- **Python Version:** **Python 3.10.12** (`/usr/bin/python3`)
- **ROS 2 Distribution:** **ROS 2 Humble Hawksbill** (`/opt/ros/humble`)
- **Workspace Directories:**
  - `/home/yash/ranger_mini_humble_ws`
  - `/home/yash/ros2_ws`
  - `/home/yash/open_manipulator`
- **Suitability:** Primary candidate for Isaac Sim Docker containers, ROS 2 Humble drivers, and MoveIt 2.

### 2.2 WSL2: Ubuntu 26.04 (`lyrical`)
- **Kernel:** Linux 6.6.x x86_64
- **Primary User:** `yash` (`/home/yash`)
- **Python Version:** **Python 3.14.4** (`/usr/bin/python3`)
- **ROS 2 Distribution:** **ROS 2 Lyrical Llama** (`/opt/ros/lyrical`)
- **Workspace Directories:**
  - `/home/yash/ranger_mini_lyrical_2604_ws`
  - `/home/yash/ranger_mini_lyrical_2604_project`
- **MoveIt 2 Configurations:** Contains verified `ranger_piper.srdf` with planning groups `piper_arm` and `piper_gripper`.

### 2.3 Windows 11 Native Host Environment
- **Python Version:** **Python 3.11.9** (`MSC v.1938 64 bit (AMD64)`)
- **PyTorch Host Version:** **2.12.1+cpu** (CPU fallback on Windows host environment)
- **Workspaces:** `D:\yaswanth\ranger mini\jarvis-piper`, `D:\yaswanth\lerobot`

---

## 3. NVIDIA Isaac Sim & Isaac Lab Installation Status

- **Omniverse / Isaac Sim Discovery:**
  - Audited candidate paths:
    - `~/.local/share/ov/pkg/isaac-sim-*` (Absent)
    - `C:\Users\recvn\AppData\Local\ov\pkg\*` (Absent)
    - `C:\Program Files\NVIDIA Corporation\*` (No standalone Omniverse launcher)
- **Current Isaac Sim State:** **NOT INSTALLED AS STANDALONE LOCAL DESKTOP BINARY**.
- **Execution Strategy:**
  1. Headless kinematic, physics, and synthetic vision simulation pipeline implemented via `PiperKinematics`, SE(3) transforms, and deterministic mock adapters.
  2. Containerized Isaac Sim 4.2+ execution pathway documented via NVIDIA NGC container:
     ```bash
     docker run --name isaac-sim --entrypoint bash -it --gpus all -e "ACCEPT_EULA=Y" --network=host nvcr.io/nvidia/isaac-sim:4.2.0
     ```

---

## 4. Hardware Verification & Interface Status

### 4.1 AgileX PiPER 6-DOF Robotic Arm
- **Current Setup:** **ONE PHYSICAL ARM** is configured.
- **Actuator Architecture:** 6 revolute joints powered by CAN bus brushless servos.
  - Joint 1 (Base Yaw): $[-2.618, +2.618]\,\text{rad}$ ($[-150^\circ, +150^\circ]$)
  - Joint 2 (Shoulder Pitch): $[0.0, +3.1415]\,\text{rad}$ ($[0^\circ, +180^\circ]$)
  - Joint 3 (Elbow Pitch): $[-2.967, 0.0]\,\text{rad}$ ($[-170^\circ, 0^\circ]$)
  - Joint 4 (Wrist Roll): $[-1.745, +1.745]\,\text{rad}$ ($[-100^\circ, +100^\circ]$)
  - Joint 5 (Wrist Pitch): $[-1.221, +1.221]\,\text{rad}$ ($[-70^\circ, +70^\circ]$)
  - Joint 6 (Wrist Yaw): $[-2.0944, +2.0944]\,\text{rad}$ ($[-120^\circ, +120^\circ]$)
- **Parallel Gripper:** Prismatic bilateral stroke $[0.0, 0.070]\,\text{m}$ ($0.035\,\text{m}$ per finger).
- **Communication Bus:** SocketCAN (`can0`) at 1,000,000 bps (1 Mbps).
- **URDF Model:** Mathematically validated and verified in `piper.urdf`.
- **Hardware Connection:** Currently disconnected / unpowered during software auditing. Defaulting to SIMULATION mode.

### 4.2 AgileX PIKA Sense Spatial Teleoperation Hub
- **Tracking Technology:** HTC Vive Lighthouse v2.0 SteamVR optical tracking protocol.
- **Hardware USB VID/PID:** `0x28de` (Valve Software wireless receiver).
- **Driver Integration:** Requires `81-vive.rules` udev configuration and `libsurvive` SteamVR daemon.
- **Documentation:** Verified in `D:\yaswanth\ranger mini\Pika Product User Manual beta（EN）ROS2.md`.
- **Status:** Hardware receiver unplugged; fallback simulation adapter active.

### 4.3 Perception Sensors
- **Physical Camera:** RealSense RGB-D camera / USB camera.
- **Trained YOLO11 Model:** `Jarvis_Object_Detection.v1i.yolov11/yolo11n.pt` fine-tuned on classes `['bowl', 'cup', 'red block']`.
- **Pinhole Deprojection:** Tested and passing in `jarvis_piper.perception.detector`.
