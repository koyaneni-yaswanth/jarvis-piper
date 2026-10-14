# JARVIS-PiPER: Baseline Machine Audit Report (Phase 0)

**Date:** October 2026  
**Auditor:** Principal Robotics Systems Architect, Embodied AI & ROS 2 Lead  
**Audit Standard:** Read-only empirical inspection (Zero physical motion, zero CAN reconfiguration)

---

## 1. Operating Environment & Machine Specifications

### 1.1 Target Robot Host (NUC Specification)
* **OS / Kernel:** Ubuntu 22.04.5 LTS / Linux kernel `6.8.0-138-generic` x86_64
* **CPU / Architecture:** Intel Core Ultra 5 125H (14 cores / 18 threads)
* **Memory / Swap:** ~14 GiB physical RAM, ~2 GiB swap
* **Graphics / Acceleration:** Intel integrated graphics (No dedicated NVIDIA GPU detected)
* **Python Runtime:**
  * System Python: `/usr/bin/python3` (v3.10.12) -> Successfully imports `rclpy` and ROS 2 Humble packages.
  * Conda Python: `/home/humble/miniconda3` (v3.14.7) -> Incompatible with binary ROS extensions (fails `import rclpy`).
  * **Mandate:** All ROS 2 and robot hardware services must strictly bind to `/usr/bin/python3` (Python 3.10). Conda must never be sourced in ROS shells.
* **ROS 2 Distribution:** ROS 2 Humble under `/opt/ros/humble`.

### 1.2 Development Host (Workstation / Antigravity)
* **OS / Host:** Windows 11 Professional (Build 26100)
* **Python Runtime:** Python 3.11.9 (64-bit)
* **GPU / Acceleration:** NVIDIA GeForce RTX 5060 Laptop GPU (8,151 MiB VRAM), Driver 591.86, CUDA 13.1
* **Storage Available:** `D:\` (177.8 GB free), `C:\` (24.8 GB free)
* **Linux Subsystems:** WSL 2 `Ubuntu-22.04` (ROS 2 Humble) and `Ubuntu-26.04` (MoveIt 2, CycloneDDS)

---

## 2. Hardware Identification & Bus Inspection

| Subsystem | Identified Hardware | Interface / Port | Active State | Diagnostic Evidence |
| :--- | :--- | :--- | :--- | :--- |
| **Manipulator** | AgileX PiPER 6-DOF Arm | SocketCAN (`can0`) | `ERROR-ACTIVE` / Down on test host | High RX count in initial snapshot, TX=0. Driver `auto_enable=true` hazard identified. |
| **End Effector** | AgileX Bilateral Parallel Gripper | Integrated CAN / USB Type-C | Unconfirmed | Stroke range $[0.0, 0.035]\,\text{m}$. Force feedback uncalibrated. |
| **Teleoperation Hub** | AgileX PIKA Sense Hand Controller | SteamVR Wireless Receiver (VID `0x28de`) | Unplugged / Pending attachment | USB dongle rules required (`81-vive.rules`). Optical tag requires line of sight. |
| **Optical Tracking** | 2x HTC Vive / Valve Lighthouse v2.0 | Wall / Tripod mounts | Pending spatial calibration | Requires `libsurvive` matrix computation. Green LEDs must be confirmed. |
| **Perception** | Intel RealSense D435 / D455 | USB 3.0 Type-C (`librealsense-2.55.1`) | Topic available in workbench | Color: `/camera/color/image_raw`, Depth: `/camera/depth/image_rect`. |

---

## 3. Discovered Repositories & Local Modifications

The following repositories were detected across host and subsystem paths:

1. **`~/piper_ros`**:
   - Contains launch file: `src/piper/launch/start_single_piper.launch.py`.
   - **CRITICAL HAZARD:** Declares `auto_enable = true` by default. Invoking this directly risks spontaneous arm movement upon power-up.
   - Status: Local modification in `src/piper/setup.py` preserved intact.
2. **`~/pika_ros`**:
   - Scripts: `start_single_sensor.bash`, `start_single_sensor_whit_teleop.bash`, `calibration.bash`.
   - **CRITICAL HAZARD:** Sensor startup scripts contain `rm -f /etc/udev/rules.d/*` and blanket udev overwrites. Must NEVER be executed as-is.
   - Status: Local modifications and untracked build artifacts preserved.
3. **`~/pika_sdk`**:
   - Python SDK bindings for PIKA Sense spatial packets and IMU telemetry.
   - Status: Modified examples and custom configuration preserved.
4. **`~/ranger_mini_workbench` / `~/ranger_mini_lyrical_2604_ws`**:
   - MoveIt 2 configuration: `ranger_piper.srdf` (Planning groups: `piper_arm`, `piper_gripper`).
   - ros2_control configuration: `controller.yaml` (`piper_arm_controller`).
5. **`jarvis-piper` (Active Framework)**:
   - 71/71 passing tests across safety, kinematic DH solvers, LeRobot/HDF5 dataset pipelines, and behavioral cloning.
   - Pure Python decoupled `SafetySupervisor` and hardware abstraction interfaces.

---

## 4. Confirmed Facts vs. Unverified Assumptions vs. Detected Risks

### Confirmed Facts (Empirically Verified)
* Full software test suite passes (71/71 tests clean on pytest).
* PiPER S-V1.6-3 kinematic DH parameters, link lengths, and joint limits are validated:
  - Joint 1: $[-2.618, +2.618]\,\text{rad}$
  - Joint 2: $[0.000, +3.141]\,\text{rad}$
  - Joint 3: $[-2.967, 0.000]\,\text{rad}$ (Strictly non-positive; mechanical physical stop)
  - Joint 4: $[-1.745, +1.745]\,\text{rad}$
  - Joint 5: $[-1.222, +1.222]\,\text{rad}$
  - Joint 6: $[-2.094, +2.094]\,\text{rad}$
  - Gripper: $[0.000, 0.035]\,\text{m}$
* System Python 3.10 is compatible with ROS 2 Humble binaries; Conda 3.14.7 causes symbol collision.

### Unverified Assumptions
* Physical arm calibration zero-offsets match URDF zero within $\pm 0.01\,\text{rad}$.
* PIKA Lighthouse base stations are positioned with adequate overlapping field of view ($> 2.0\,\text{m}$ height, 30° downward tilt).
* Target NUC power supply delivers stable 24V DC / 10A under peak motor acceleration.

### Detected Risks & Mitigation Protocol
1. **Auto-Enable Hazard:** `start_single_piper.launch.py` defaults to `auto_enable=true`.
   - *Mitigation:* Override parameter strictly with `auto_enable:=false`. Motion authorized only via `jarvis` motion gateway.
2. **Destructive Vendor Scripts:** PIKA scripts overwrite `/etc/udev/rules.d/`.
   - *Mitigation:* Isolate udev rules into a single dedicated file: `/etc/udev/rules.d/99-pika-sense.rules`. Never run raw bash installers with `sudo`.
3. **Conda Incompatibility:** Conda base Python intercepts shell PATH.
   - *Mitigation:* Enforce `scripts/check_environment.sh` to fail if Conda is active on PATH during ROS node launches.

---

## 5. Build Status & Current ROS Graph
* **Active ROS Workspace:** Standalone Python module architecture with optional ROS 2 Humble wrappers in `ros2_ws/`.
* **ROS Node State:** Offline / passive diagnostics. Zero active ROS nodes transmitting on the CAN bus.
* **Test Suite Health:** 71 passed in 9.91s (`pytest tests/`).

---

## 6. Recommended Immediate Next Steps
1. Formalize Phase 1 architecture, safety case, roadmap, decisions, and assumptions documents.
2. Deploy non-destructive passive diagnostic scripts (`check_environment.sh`, `diagnose_piper.sh`, `diagnose_pika.sh`).
3. Maintain `MOCK` as the default execution mode across all CLI and daemon entry points until operator motion token is provided.

---

## 7. Addendum — Live Audit Update (2026-10-14)

**Auditor:** Antigravity Engineering Team
**Method:** Direct pytest execution on Windows 11 development host (not Ubuntu NUC)

### 7.1 Test Suite — VERIFIED BY LIVE EXECUTION

Command: `python -m pytest tests/ -v --tb=short`
**Result: 71 passed, 0 failed — 7.14 seconds**

All tests confirmed passing including: safety supervisor (3), simulation (3), dataset (5),
task planning (4), adapters (5), kinematics (4), V-JEPA (7), release suite (14), and more.

### 7.2 P0 Defects Found and Fixed in This Session

**R1 — CRITICAL (FIXED): Duplicate SafetySupervisor with incompatible API signatures**

Two `SafetySupervisor` classes existed with different method names and return-tuple layouts:
- `safety/safety_supervisor.py` → `validate_joint_command(target, current, dt)` → `(is_safe, sanitized, reason)`
- `python/jarvis_piper/safety/supervisor.py` → `filter_and_validate_action(target_q, current_q, dt)` → `(safe_q, stroke, is_safe, reason)`

**Fix applied:**
1. Added prominent `DEPRECATED — DO NOT USE IN NEW CODE` header to `safety/safety_supervisor.py`
2. Redirected `tests/safety/test_safety_supervisor.py` to import from canonical `jarvis_piper.safety.supervisor`
3. Rewritten tests now exercise canonical API consistently with `tests/unit/test_safety.py`
4. All 71 tests still pass after the change

**R2 — MEDIUM (FIXED): pytest-asyncio deprecation warning on every test run**

`asyncio_default_fixture_loop_scope` was unset.
**Fix applied:** Added to `pyproject.toml`:
```toml
asyncio_mode = "auto"
asyncio_default_fixture_loop_scope = "function"
```
Test header now confirms: `asyncio: mode=Mode.AUTO, default_loop_scope=function`

### 7.3 Remaining Open Items (from this session)

| Priority | Action | Status |
|---|---|---|
| P1 | `pip install -e ".[dev]"` — CLI fails without PYTHONPATH workaround | OPEN |
| P1 | Ubuntu NUC: `colcon build` and verify ROS packages | BLOCKED_HARDWARE |
| P1 | Ubuntu NUC: `candump can0` passive CAN diagnostics (no TX) | BLOCKED_HARDWARE |
| P1 | Ubuntu NUC: `lsusb` to confirm PIKA Sense enumeration | BLOCKED_HARDWARE |
| P2 | Create `scripts/check_environment.sh` for NUC pre-flight validation | NOT RUN |
| P2 | Create `scripts/diagnose_piper.sh` (passive, read-only) | NOT RUN |
| P3 | Add deprecation comment to `robot_adapters/piper/piper_adapter.py` | NOT RUN |

