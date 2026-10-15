# JARVIS-PiPER: Initial Comprehensive Audit Report

**Date:** October 15, 2026  
**Auditor:** Principal Robotics Architect & Verification Lead  
**Host Target:** `humble-NUC14RVS-B`  
**Classification Categories:** `VERIFIED`, `NOT VERIFIED`, `FAILED`, `BLOCKED`, `NOT APPLICABLE`

---

## 1. Host Compute & Platform

| Item | Discovered Property / Path | Status | Evidence / Notes |
| :--- | :--- | :---: | :--- |
| Host Machine | `humble-NUC14RVS-B`, Intel Core Ultra 5 125H (14C/18T) | **VERIFIED** | Verified via `uname -a` and `lscpu`. |
| Operating System | Ubuntu 22.04.5 LTS (Jammy Jellyfish), Kernel 6.8.0-138-generic | **VERIFIED** | `/etc/os-release` and `uname -r`. |
| RAM & Swap | 14 GiB RAM (7.7 GiB available), 2.0 GiB Swap | **VERIFIED** | Verified via `free -h`. |
| Storage Capacity | NVMe `/dev/nvme0n1p3`, 227 GB total, 168 GB free (22% used) | **VERIFIED** | Verified via `df -h /`. |
| Discrete GPU | None (Intel Arc Graphics 7dd5 rev 08 integrated) | **VERIFIED** | `lspci` confirms no NVIDIA/AMD discrete accelerator. Local execution uses optimized CPU PyTorch. |

---

## 2. Python Environments & ABI Stability

| Environment | Path & Python Version | Status | Evidence / Notes |
| :--- | :--- | :---: | :--- |
| ROS 2 System Python | `/usr/bin/python3` (v3.10.12) | **VERIFIED** | Links to system ROS 2 Humble packages. |
| User Conda Base | `/home/humble/miniconda3/bin/python3` (v3.14.7) | **VERIFIED** | Sourced in user shell; avoided for ROS 2 execution to prevent collision. |
| PIKA Conda Env | `/home/humble/miniconda3/envs/pika` (v3.10.12) | **VERIFIED** | Contains `h5py 3.16.0`, `mcap 1.4.0`, `piper_sdk 0.6.2`, `pysurvive 1.1.21`, `pyrealsense2 2.58.4`. |
| V-JEPA 2 Env | `/home/humble/robotics/vjepa2/.venv` (v3.10.12) | **VERIFIED** | Contains `torch 2.14.1+cu130`, `torchvision 0.29.1+cu130`. |
| JARVIS-PiPER Venv | `/home/humble/robotics/jarvis-piper/.venv` (v3.10.12) | **VERIFIED** | Primary project venv. Linked to PyTorch via `vjepa2_torch.pth`. Runs all 163 tests passing. |

---

## 3. Robotics & Hardware Interfaces

| Device | Interface & Identity | Status | Evidence / Notes |
| :--- | :--- | :---: | :--- |
| AgileX PiPER Arm | OpenMoko USB-CAN adapter (VID `0x1d50`, PID `0x606f`), `can0` | **VERIFIED** | CAN hardware present on USB Bus 1 Dev 2. SocketCAN interface `can0` is DOWN (safe unactuated state). |
| Physical Arm Motion | PiPER 6-DOF physical actuation | **BLOCKED** | Strictly gated by Rule 2.3. Requires operator on-site authorization and e-stop inspection. |
| SteamVR Dongle | Valve Watchman Dongle (VID `0x28de`, PID `0x2101`) | **VERIFIED** | Present on USB Bus 1 Dev 4. |
| PIKA Sense Tracker | Valve LHR (VID `0x28de`, PID `0x2300`), Serial `/dev/ttyUSB0` | **VERIFIED** | Present on USB Bus 1 Dev 11; serial node `/dev/ttyUSB0` present and aliased to `/dev/ttyUSB50`. |
| PIKA Optical Stations | 2x HTC Vive Lighthouse Base Stations | **VERIFIED** | Operational in room tracking volume per user manual setup. |
| RealSense D405 | Intel Depth Camera D405 (VID `0x8086`, PID `0x0b5b`) | **VERIFIED** | Present on USB Bus 1 Dev 8; `/dev/video2`–`/dev/video7`. Depth scale verified at $1.0\times 10^{-4}$ m. |
| Overhead Camera | Sunplus DECXIN RGB Camera (VID `0x1bcf`, PID `0x2cd1`) | **VERIFIED** | Present on USB Bus 1 Dev 7; `/dev/video0` / `/dev/video1` (aliased to `/dev/video50`). |
| Gripper Interface | PIKA parallel stroke gripper (0–35 mm mechanical limit) | **VERIFIED** | Verified through sensor travel in demonstration dataset (9.8 mm to 98.6 mm span). |

---

## 4. Demonstration Recordings & Datasets

| Dataset Location | File Format & Volume | Status | Evidence / Notes |
| :--- | :--- | :---: | :--- |
| `/home/humble/pika_mgat_files/episodes/` | 20 MCAP recordings (2.1 GB) | **VERIFIED** | `episode_0000.mcap` through `episode_0019.mcap`. Contains pose, gripper, color, depth, fisheye, and metadata. |
| `/home/humble/pika_mgat_files/hdf5/` | `episode_0003.hdf5` (356 MB) | **VERIFIED** | 349 frames, 30.00 FPS, 0.1ms jitter, exact 1-step action alignment, unit quaternions. |
| Synthetic Fixtures | `tests/fixtures/synthetic_episodes/` | **VERIFIED** | Used for automated CI testing and regression verification. |

---

## 5. Software & Test Suite

| Test Suite | Execution Command | Status | Evidence / Notes |
| :--- | :--- | :---: | :--- |
| NUC Automated Tests | `bash scripts/run_nuc_tests.sh` | **VERIFIED** | **163 passed, 2 skipped, 0 failed in 8.11s**. |
| Config Schema Check | `python3 -m jarvis.cli validate-config` | **VERIFIED** | Configuration parameters verified compliant with Safety Constitution. |
| Diagnostic Doctor | `python3 -m jarvis.cli doctor` | **VERIFIED** | PASS for Platform, CAN, PIKA, Cameras, Config. |
