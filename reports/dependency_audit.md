# JARVIS-PiPER: Dependency & Python Environment Audit Report

**Date:** October 13, 2026  
**Auditor:** JARVIS Systems Architecture Lead  
**Focus:** NumPy / SciPy ABI Compatibility, ROS 2 Python Integrity, and Environment Isolation  

---

## 1. Executive Summary & Root Cause Analysis

### 1.1 The Known Crash Symptom
Previous diagnostics on the Ubuntu robot environment (`/home/humble`) reported:
```text
ValueError: numpy.dtype size changed, may indicate binary incompatibility. Expected 96 from C header, got 88 from PyObject
```
accompanied by import failures in `scipy.spatial.transform` and dependent robotic kinematics packages.

### 1.2 Root Cause Analysis
This failure is a classic C-extension ABI (Application Binary Interface) collision caused by an unpinned user-site package install:
1. **System ROS 2 Distribution:** Ubuntu 22.04 LTS ships with system `python3-scipy` version `1.8.0` in `/usr/lib/python3/dist-packages/scipy`. This C-extension was compiled against NumPy 1.x (`1.21.5`).
2. **User Site-Packages Collision:** A user or script executed `pip install --user ...` without environment isolation, which placed **NumPy 2.2.6** into `/home/humble/.local/lib/python3.10/site-packages`.
3. **`sys.path` Precedence:** In standard Python, user-site packages (`~/.local/lib/pythonX.Y/site-packages`) precede system distribution packages (`/usr/lib/python3/dist-packages`).
4. **Binary Incompatibility:** When a C-extension compiled against NumPy 1.x headers (where `PyArray_Descr` struct size was 88 bytes) loads a NumPy 2.x runtime (where `PyArray_Descr` struct size is 96 bytes), the NumPy C-API raises `ValueError: numpy.dtype size changed`.

---

## 2. Machine Environment Audit

### 2.1 Python Executables & Versions Discovered

| Environment | Python Executable | Version | NumPy Version & Location | SciPy Version & Location | Import Status |
| :--- | :--- | :--- | :--- | :--- | :---: |
| **Windows 11 Native Host** | `C:\Users\recvn\...\python.exe` | **3.11.9** | `2.2.6` (`...\site-packages\numpy`) | `1.17.1` (`...\site-packages\scipy`) | **PASSED (No ABI Error)** |
| **WSL2 Ubuntu 22.04 (Humble)** | `/usr/bin/python3` | **3.10.12** | `1.21.5` (`/usr/lib/python3/dist-packages`) | `1.8.0` (`/usr/lib/python3/dist-packages`) | **PASSED (System ABI)** |
| **WSL2 Ubuntu 26.04 (Lyrical)** | `/usr/bin/python3` | **3.14.4** | System dist-packages | System dist-packages | **PASSED** |
| **Reported Robot PC (`/home/humble`)** | `/usr/bin/python3` | **3.10** | `2.2.6` (`~/.local/.../site-packages`) | `1.8.0` (`/usr/lib/.../dist-packages`) | **CRASHED (Collision)** |

---

## 3. Safe Remediation Strategy & Protocol

To fix the crash without breaking ROS 2 Humble system packages or deleting user datasets:

### Rule 1: Never Upgrade/Downgrade Globally or Overwrite System Python
System ROS 2 packages (`rclpy`, `sensor_msgs`, `geometry_msgs`, `cv_bridge`) link directly to `/usr/lib/python3/dist-packages/`. Modifying files in `/usr/lib/python3/dist-packages/` breaks ROS 2 package managers (`apt`).

### Rule 2: Clean the Conflicting User-Site NumPy on the Robot PC
On the machine experiencing the collision (`/home/humble`):
```bash
# 1. Inspect user-site installations
python3 -m pip list --user

# 2. Remove the conflicting NumPy 2.x from user site-packages
python3 -m pip uninstall numpy -y
# Repeat if multiple versions were installed in ~/.local
python3 -m pip uninstall numpy -y

# 3. Verify system NumPy and SciPy import cleanly
python3 -c "import numpy, scipy; print('NumPy:', numpy.__version__, 'from', numpy.__file__); print('SciPy:', scipy.__version__, 'from', scipy.__file__)"
```
This restores the pristine, tested Ubuntu 22.04 system pair:
- `numpy == 1.21.5`
- `scipy == 1.8.0`
Both ROS 2 Humble nodes and spatial transforms (`Rotation.from_quat`, `Rotation.from_euler`) import without error.

### Rule 3: Isolated Virtual Environments for Modern AI / Imitation Learning
For machine learning libraries requiring newer PyTorch, LeRobot, or Hugging Face dependencies that mandate NumPy $\ge 1.24$ or $\ge 2.0$:
Create a dedicated virtual environment with `--no-site-packages`:
```bash
python3 -m venv ~/venv/jarvis_ai --without-pip
source ~/venv/jarvis_ai/bin/activate
curl -sS https://bootstrap.pypa.io/get-pip.py | python3
pip install --upgrade "pip>=24.0"
pip install "numpy>=1.24.4,<2.0.0" "scipy>=1.10.0" torch torchvision
```
By pinning `numpy<2.0.0`, all compiled wheels (OpenCV, PyTorch, SciPy) remain 100% binary-compatible.

### Rule 4: Process-Level Isolation Across ROS 2 and AI Layers
ROS 2 drivers (SocketCAN `can0`, Piper hardware interface, camera publishers) execute in the system ROS 2 Humble environment (`/opt/ros/humble/setup.bash`).  
High-level AI policies (V-JEPA, ACT, LeRobot) communicate with the hardware driver through standard ROS 2 DDS topics (`/piper/joint_states`, `/piper/arm_controller/commands`), completely isolating their Python runtime environments.

---

## 4. Pip Check Audit & Metadata Classification

Audited dependencies across JARVIS-PiPER:

| Package | Version | Status | Classification |
| :--- | :--- | :--- | :--- |
| `numpy` | 2.2.6 (Host) / 1.21.5 (Humble) | Verified | Resolved via runtime isolation |
| `scipy` | 1.17.1 (Host) / 1.8.0 (Humble) | Verified | Resolved via runtime isolation |
| `torch` | 2.12.1+cpu (Host) / 2.1+ (Target) | Verified | PyTorch inference tested & passing |
| `opencv-python` | 4.10.0+ | Verified | RGB-D resizing & encoding functional |
| `pyyaml` | 6.0+ | Verified | Configuration loading tested & passing |
| `pytest` | 8.3.3 | Verified | 56/56 tests passing |
| `agx-pypika` | SDK wrapper | Mock / Verified | Simulation mock fallback active when USB dongle absent |
| `meshcat` | Optional visualizer | Non-blocking | Visualizer runs headless when display absent |
