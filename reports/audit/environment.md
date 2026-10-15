# JARVIS-PiPER: Real Environment Audit Report

**Date:** October 15, 2026  
**Auditor:** JARVIS Systems Architecture Lead  
**Host Target:** `humble-NUC14RVS-B`  
**Execution Mode:** Local Direct Verification (Non-Destructive)

---

## 1. Operating System & Host Compute Platform

| Attribute | Measured Host Value | Verification Method | Status |
| :--- | :--- | :--- | :---: |
| **Hostname** | `humble-NUC14RVS-B` | `uname -a` | PASS |
| **OS Distribution** | Ubuntu 22.04.5 LTS (Jammy Jellyfish) | `/etc/os-release` | PASS |
| **Linux Kernel** | `6.8.0-138-generic #138~22.04.1-Ubuntu SMP PREEMPT_DYNAMIC` | `uname -r` | PASS |
| **CPU Architecture** | `x86_64` | `lscpu` | PASS |
| **Processor Model** | Intel(R) Core(TM) Ultra 5 125H (14 cores / 18 threads) | `lscpu \| grep "Model name"` | PASS |
| **Total System RAM** | 14 GiB (5.3 GiB used, 7.7 GiB available) | `free -h` | PASS |
| **Swap Space** | 2.0 GiB (0 B used) | `free -h` | PASS |
| **NVMe Disk Storage** | `/dev/nvme0n1p3`: 227 GB total, 48 GB used, 168 GB available (22% capacity) | `df -h /` | PASS |

---

## 2. Python Environments & Acceleration

| Environment Path | Python Version | Primary Purpose | Key Packages Verified | Status |
| :--- | :--- | :--- | :--- | :---: |
| `/usr/bin/python3` | 3.10.12 | System ROS 2 Humble runtime | `rclpy`, `sensor_msgs`, `geometry_msgs` | PASS |
| `/home/humble/miniconda3/bin/python3` | 3.14.7 | User Conda Base | `conda 26.7.1` (warned on ROS 2 path collision) | WARN |
| `/home/humble/miniconda3/envs/pika` | 3.10.12 | Vendor PIKA / Data Collection runtime | `piper_sdk 0.6.2`, `pyAgxArm 1.0.0`, `pysurvive 1.1.21`, `pyrealsense2 2.58.4`, `h5py 3.16.0`, `mcap 1.4.0`, `rerun-sdk 0.36.3`, `numpy 1.24.4`, `scipy 1.15.2` | PASS |
| `/home/humble/robotics/vjepa2/.venv` | 3.10.12 | Meta V-JEPA 2 / PyTorch Workstation | `torch 2.14.1+cu130`, `torchvision 0.29.1+cu130`, `triton 3.8.0`, `rclpy 3.3.21` | PASS |
| `/home/humble/robotics/jarvis-piper/.venv` | 3.10.12 | Primary JARVIS-PiPER isolated venv | `pytest 9.1.1`, `numpy 2.2.6`, `pyyaml 6.0.3`, `torch 2.14.1+cu130` (linked via `.pth`), `rclpy 3.3.21` | PASS |

### Accelerator & GPU Findings
- **Discrete GPU:** None detected on NUC host (`lspci` reports `00:02.0 VGA: Intel Corporation Device 7dd5 (rev 08)` - integrated Intel Arc Graphics).
- **PyTorch Device:** CPU device execution confirmed for local validation; heavy foundation training offloaded to workstation or synthetic evaluation harness.

---

## 3. ROS 2 Installation & Workspaces

- **Distribution:** ROS 2 Humble Hawksbill (`/opt/ros/humble`)
- **RMW Implementation:** Default Fast-DDS
- **Discovered Workspaces:**
  1. `/home/humble/piper_ros`: Vendor AgileX PiPER ROS 2 drivers (`piper`, `piper_description`, `piper_msgs`, `piper_moveit`, `piper_sim`).
  2. `/home/humble/pika_ros`: Vendor AgileX PIKA ROS 2 teleoperation suite (`data_msgs`, `data_tools`, `PikaAnyArm`, `realsense-ros`, `sensor_tools`).
  3. `/home/humble/robotics/jarvis-piper/ros2_ws`: JARVIS-PiPER production ROS 2 packages (`jarvis_piper_bringup`, `jarvis_piper_dataset`, `jarvis_piper_interfaces`, `jarvis_piper_monitor`, `jarvis_piper_perception`, `jarvis_piper_recorder`, `jarvis_piper_replay`, `jarvis_piper_sync`, `jarvis_piper_tools`, `jarvis_piper_world_model`).
  4. `/home/humble/ros2_workspace`: Auxiliary local workspace.

---

## 4. Git Repository Integrity

- **Directory:** `/home/humble/robotics/jarvis-piper`
- **Current Branch:** `main` (tracked to `origin/main`)
- **HEAD Commit:** `fecfb4a` (*fix(deployment): add lark dependency, isolate pytest from launch_testing, and add NUC recovery script*)
- **Working Tree State:** Clean; non-destructive preservation confirmed.
- **Safety Backups:** Existing verified snapshots preserved in `/home/humble/jarvis_backup_*` and `/home/humble/jarvis_piper_backup_*`.
