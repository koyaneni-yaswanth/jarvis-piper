# JARVIS Phase 0: System Compatibility Matrix

**Target Robot:** ONE AgileX PiPER 6-DOF Manipulator + PIKA Sense Hub  
**Host Architecture:** Windows 11 + WSL2 Ubuntu-22.04 + WSL2 Ubuntu-26.04  

---

## 1. System & Environment Compatibility

| Component / Layer | Required / Reference Version | Installed System Version | Compatibility Status | Technical Analysis & Mitigation |
| :--- | :--- | :--- | :---: | :--- |
| **Host OS** | Windows 11 / Ubuntu 22.04 LTS | Windows 11 (Host) + Ubuntu 22.04 & 26.04 (WSL2) | **COMPATIBLE** | Hybrid architecture: Python algorithms & CLI run natively on Windows host; ROS 2 builds run under WSL2. |
| **GPU Hardware** | NVIDIA RTX 30-series / 40-series / 50-series | NVIDIA GeForce RTX 5060 (8 GB VRAM) | **COMPATIBLE** | 8 GB VRAM supports batch size 2–4 for V-JEPA ViT-B inference and ACT/BC policy training. |
| **NVIDIA Driver** | $\ge 535.129$ | **591.86** (WDDM 3.2) | **COMPATIBLE** | Fully compatible with CUDA 12.x and 13.x workloads and Isaac Sim 4.2+. |
| **CUDA Toolkit** | CUDA 12.1 / 12.4 | **CUDA 13.1** (Driver Level) | **COMPATIBLE** | PyTorch Wheels with CUDA 12.4+ operate smoothly under driver 591.86. |
| **Python Environment** | Python 3.10 or 3.11 | Python 3.11.9 (Win), Python 3.10.12 (WSL 22.04) | **COMPATIBLE** | Python 3.10 is pinned for ROS 2 Humble; Python 3.11 is used for JARVIS-PiPER host CLI & PyTorch. |
| **ROS 2 Distribution** | ROS 2 Humble (LTS) | ROS 2 Humble (`/opt/ros/humble` on WSL 22.04) | **COMPATIBLE** | Native MoveIt 2 Humble binaries present in Ubuntu 22.04. |
| **NVIDIA Isaac Sim** | Isaac Sim 4.2.0 / 4.1.0 | Standalone binary absent; Container ready | **BLOCKED (LOCAL BINARY)** | Requires either Omniverse Launcher installation (25 GB download) or headless container execution via Docker. Validated headless kinematic simulation acts as active fallback. |
| **Isaac Lab** | Isaac Lab v1.1.0+ | Not installed | **BLOCKED (DEPENDENCY)** | Blocked by Isaac Sim binary prerequisite. Reinforcement learning pilots run in simulation fallback. |
| **Meta V-JEPA 2 / 2-AC** | PyTorch $\ge 2.1$, Timm, Torchvision | PyTorch 2.12.1+cpu (Host), CUDA available on GPU | **COMPATIBLE (WITH CPU FALLBACK)** | Architectural ViT encoder and Action-Conditioned Latent Predictor implemented and verified in `world_model/vjepa`. |
| **Piper SDK & CAN** | `python-can`, SocketCAN | `python-can 4.4.2` | **COMPATIBLE** | SocketCAN available in Linux kernel; Mock adapter available on Windows. |
| **PIKA Sense Driver** | `libsurvive`, SteamVR udev | Manual verified in `D:\yaswanth` | **COMPATIBLE (HARDWARE DISCONNECTED)** | Physical tracker USB VID `0x28de` requires in-room Lighthouse 2.0 calibration. |
| **MoveIt 2 Planning** | MoveIt 2 SRDF | `ranger_piper.srdf` configured | **COMPATIBLE** | Planning groups `piper_arm` and `piper_gripper` verified. |
| **Object Detection** | Ultralytics YOLO11 | YOLO11n fine-tuned weights (`yolo11n.pt`) | **COMPATIBLE** | Model loaded, tested, and passing with 3D pinhole deprojection. |

---

## 2. API & Dependency Constraints

### 2.1 PyTorch & CUDA Execution Pathway
- **Current Host Status:** PyTorch is running `2.12.1+cpu` on the Windows host.
- **Impact:** V-JEPA and policy training execute in CPU mode on the host, which is deterministic and lightweight for unit testing and smoke rollouts.
- **GPU Acceleration Pathway:** For large-scale V-JEPA pretraining across thousands of frames, install `torch torchvision --index-url https://download.pytorch.org/whl/cu124` to unlock the full 8 GB RTX 5060 Tensor Core acceleration.

### 2.2 Simulation Mode vs. Hardware Execution
- **Strict Boundary:** The simulation pipeline NEVER sends CAN frames or commands to the physical robot (`can0`) by default.
- **Execution Switching:** Switching from SIMULATION to PHYSICAL requires:
  1. Setting `execution_mode: "HARDWARE"` in `configs/piper.yaml`.
  2. Physical CAN bus bringup: `sudo ip link set can0 up type can bitrate 1000000`.
  3. Interactive operator confirmation and emergency-stop clearance.
