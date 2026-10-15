# JARVIS-PiPER: Dependency & Environment Audit Report

**Date:** October 15, 2026  
**Auditor:** JARVIS Systems Architecture Lead  
**Scope:** Python Environment Resolution, ABI Compatibility, and Framework Isolation

---

## 1. Environment Architecture & ABI Resolution

The target robot computer (`humble-NUC14RVS-B`) maintains multi-runtime requirements spanning ROS 2 Humble C++ bindings, vendor teleoperation libraries, and deep learning policy training.

### 1.1 Resolution of Historical NumPy 2.x ABI Collision
- **Problem Statement:** User-site packages in `~/.local` previously collided NumPy 2.x with Ubuntu 22.04 system `python3-scipy` (1.8.0), causing `ValueError: numpy.dtype size changed`.
- **Enforced Architecture:**
  1. Primary development and automated test execution is strictly confined to `.venv` (`/home/humble/robotics/jarvis-piper/.venv`).
  2. In `.venv`, `numpy` is pinned to modern release (`2.2.6`), paired with binary-compatible `scipy` (`1.15.2`).
  3. C-extensions compiled for ROS 2 Humble (`rclpy`, `geometry_msgs`, `sensor_msgs`) load cleanly without ABI degradation.

### 1.2 Cross-Environment PyTorch Linking
- **Observation:** `torch 2.14.1+cu130` and `torchvision 0.29.1+cu130` are pre-compiled and present in `/home/humble/robotics/vjepa2/.venv`.
- **Implementation:** Non-destructively linked into JARVIS `.venv` via `/home/humble/robotics/jarvis-piper/.venv/lib/python3.10/site-packages/vjepa2_torch.pth`.
- **Result:** Native CPU/CUDA PyTorch import in `.venv` with zero disk bloat or network downloads.

### 1.3 Pytest Pluggy & ROS 2 Humble Isolation
- **Problem Statement:** ROS 2 Humble provides `/opt/ros/humble/lib/python3.10/site-packages/launch_testing_ros_pytest_entrypoint.py`. In pytest 9.x, the legacy hook `pytest_launch_collect_makemodule` causes `PluginValidationError`.
- **Enforced Solution:**
  1. Configured `export PYTEST_DISABLE_PLUGIN_AUTOLOAD=1` in `scripts/run_nuc_tests.sh`.
  2. Isolated pytest collection from legacy system plugins.
  3. Result: **163 passing unit and integration tests (0 failures)**.

---

## 2. Audited Dependency Matrix

| Package | Tested Version | Runtime Location | Verification Status |
| :--- | :--- | :--- | :---: |
| `python` | 3.10.12 | `.venv/bin/python` | PASS |
| `torch` | 2.14.1+cu130 | Linked from `vjepa2/.venv` | PASS |
| `torchvision` | 0.29.1+cu130 | Linked from `vjepa2/.venv` | PASS |
| `numpy` | 2.2.6 | `.venv/lib/python3.10/site-packages` | PASS |
| `scipy` | 1.15.2 | `.venv/lib/python3.10/site-packages` | PASS |
| `pyyaml` | 6.0.3 | `.venv/lib/python3.10/site-packages` | PASS |
| `pytest` | 9.1.1 | `.venv/lib/python3.10/site-packages` | PASS |
| `h5py` | 3.16.0 | `pika` conda env | PASS |
| `mcap` | 1.4.0 | `pika` conda env | PASS |
| `rerun-sdk` | 0.36.3 | `pika` conda env | PASS |
| `piper_sdk` | 0.6.2 | `pika` conda env | PASS |
| `rclpy` | 3.3.21 | Sourced ROS 2 Humble | PASS |
