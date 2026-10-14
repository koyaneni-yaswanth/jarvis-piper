# JARVIS-PiPER Deployment Audit & Readiness Report

**Audit Date:** October 2026  
**Target Host:** Physical Intel NUC (Ubuntu 22.04 LTS, ROS 2 Humble, Python 3.10.12)  
**Development Host:** Windows 11 (Python 3.11.9, RTX 5060 Laptop GPU)  
**Audit Status:** `DEPLOYMENT_READY` (Mock/Offline Verified; Real Hardware Gated)

---

## 1. Git Repository State

| Property | Value | Notes |
| :--- | :--- | :--- |
| **Active Branch** | `main` | Tracking `origin/main` |
| **Remote URL** | `https://github.com/koyaneni-yaswanth/jarvis-piper.git` | Central version-controlled origin |
| **HEAD Commit** | `bef18a5` | `fix(cli): implement teleop command and streamline dry-run mode in policy runner` |
| **Working Tree State** | Cleanly staged / uncommitted changes audited | 9 modified tracked files, 15 untracked additions |
| **Secrets & Keys** | `ZERO DETECTED` | Scanned for tokens, private keys, API keys, and credentials |
| **Hardcoded Paths** | `RESOLVED` | Dynamic environment lookup replacing developer paths; generic `$(pwd)` in docker examples |

---

## 2. Deployment Source Inventory

The following components comprise the deployable system:

### A. Core Software Layer (`jarvis/`)
- `jarvis/hardware.py`: Hardware Abstraction Layer containing `ArmInterface`, `RealPiperArm` (read-only SocketCAN frame decoder), `MockArm` (fault-injection enabled), `PikaSenseInterface`, `RealPikaSense`, and `MockTeleop`.
- `jarvis/pika_discovery.py`: Non-destructive USB (`0x28de`), serial port (`/dev/ttyACM*`), and libsurvive `config.json` discovery; `TrackingValidator` enforcing sub-50ms freshness and unit quaternion bounds.
- `jarvis/safety.py`: Central `SafetySupervisor` implementing the session motion gate (`ENABLE MOTION`), latched E-stop, dead-man clutch, milestone actuation lock, Cartesian bounding box, and `ExecutionMode` machine.
- `jarvis/errors.py`: Domain-specific actionable exception hierarchy (`MotionNotAuthorizedError`, `CanInterfaceDownError`, `StaleFeedbackError`, `CalibrationStatusError`, `DeviceNotFoundError`, etc.).
- `jarvis/doctor.py`: Non-destructive diagnostic inspector (`jarvis doctor`).
- `jarvis/cli.py`: Unified single CLI for doctor, dataset validation, dry-run teleop, demonstration recording, BC training, and policy rollout.
- `jarvis/teleop.py`: Real-time teleoperation mapper with dead-man clutch state tracking and exponential smoothing.
- `jarvis/record.py`: Demonstration data recorder and 7-point quality validator.
- `jarvis/train.py` & `jarvis/policy.py`: Behavioral cloning training and supervised execution runner.

### B. ROS 2 Workspace Layer (`ros2_ws/src/`)
- `jarvis_piper_bringup`: Launch scripts and Xacro/URDF robot model.
- `jarvis_piper_interfaces`: Custom ROS 2 msg/srv definitions for synchronized states.
- `jarvis_piper_monitor`: Web dashboard and terminal monitoring nodes.
- `jarvis_piper_recorder`: ROS 2 demonstration data recording node.
- `jarvis_piper_replay`: Trajectory playback node with safety bounds.
- `jarvis_piper_sync`: Optical and robot feedback synchronization node.

### C. Diagnostics & Deployment Scripts (`scripts/`)
- `scripts/check_environment.sh`: Host preflight audit (OS, Python, ROS 2, GPU, CAN, USB, user groups).
- `scripts/diagnose_piper.sh`: 5-step non-destructive PiPER arm and SocketCAN audit with bounded passive sniff.
- `scripts/diagnose_pika.sh`: 5-step non-destructive SteamVR dongle, serial, udev, and libsurvive audit.
- `scripts/verify_installation.sh`: Test runner checking core package imports, config, and smoke tests.

### D. Hardware Runbooks & Vendor Specs (`docs/hardware/`)
- `docs/hardware/PIPER_SETUP.md`: Wiring, 1 Mbps SocketCAN bring-up, and motor protection.
- `docs/hardware/PIPER_DIAGNOSTICS.md`: Non-destructive passive diagnostic runbook.
- `docs/hardware/PIKA_SETUP.md`: Base station placement, SteamVR dongle, and udev rules.
- `docs/hardware/PIKA_CALIBRATION.md`: Spatial calibration lifecycle and validation criteria.

---

## 3. Environment Compatibility Analysis

| Dimension | Development Host (Windows 11) | Target Host (Ubuntu NUC) | Resolution Strategy |
| :--- | :--- | :--- | :--- |
| **OS** | Windows 11 Pro 64-bit | Ubuntu 22.04.5 LTS | Cross-platform Python core in `jarvis/`; OS-specific scripts in `scripts/`. |
| **Python** | Python 3.11.9 (System) | Python 3.10.12 (System `/usr/bin/python3`) | Package metadata supports `>=3.10`. ML dependencies isolated in `requirements-ml.txt`. |
| **Conda Conflict** | N/A | Miniconda3 (`/home/humble/miniconda3`) | Deactivate Conda (`conda deactivate`) prior to sourcing ROS 2 Humble setup. |
| **ROS 2** | Mock / Off-line only | ROS 2 Humble (`/opt/ros/humble`) | Native ROS 2 build in `ros2_ws/`; Python core runs with or without ROS 2. |
| **CAN Interface** | Mocked (`MockArm`) | Physical `can0` @ 1,000,000 bps | `RealPiperArm` detects missing CAN gracefully with `CanInterfaceDownError`. |
| **USB Dongle** | Mocked (`MockTeleop`) | Physical SteamVR (VID `0x28de`) | `PikaDiscovery` audits dongle via `lsusb` and `/sys/bus/usb/devices`. |

---

## 4. Security & Safety Audit

1. **Secrets & Credentials**:
   - Zero hardcoded passwords, tokens, private keys, or API tokens detected.
   - `.gitignore` updated to strictly ignore `.env*`, `*.key`, `*.pem`, `*.token`, `*secret*`, `*credentials*`, `calibration/`, and `config.json`.
2. **Safety Invariants**:
   - Every hardware script defaults to `--dry-run`.
   - Motion requires explicit session token `"ENABLE MOTION"`.
   - In Milestone 2, physical motor actuation is locked via `milestone_lock=True`.
   - Dead-man clutch must be continuously held during teleoperation.
   - Feedback staleness ($>100\,\text{ms}$) and tracking loss ($>50\,\text{ms}$) halt commands immediately.

---

## 5. Physical NUC Deployment Blockers & Remedies

| Blocker ID | Description | Impact | Non-Destructive Remedy |
| :--- | :--- | :--- | :--- |
| **BLK-01** | `can0` down or unconfigured on NUC | Prevents real arm feedback | `sudo ip link set can0 up type can bitrate 1000000` |
| **BLK-02** | SteamVR dongle unplugged or missing udev | Prevents optical tracking | Plug dongle into USB 3.0; apply `60-pika-steamvr.rules` non-destructively |
| **BLK-03** | User not in `dialout` / `plugdev` | USB/Serial permission denied | `sudo usermod -aG dialout,plugdev $USER` (re-login required) |
| **BLK-04** | Conda environment active on NUC | ROS 2 symbol mismatch | Run `conda deactivate` before sourcing `/opt/ros/humble/setup.bash` |
| **BLK-05** | Libsurvive uncalibrated | Rejects teleop commands | Run `survive-cli --force-calibrate` with arm stationary |

---

## 6. Proposed Deployment Sequence

1. Review and commit clean changes to GitHub `main`.
2. On physical NUC, inspect Git status and fetch `origin/main` without destructive overwrites.
3. Run `scripts/check_environment.sh` to verify system preflight.
4. Run `python3 -m jarvis.cli doctor` to verify environment diagnostics.
5. Run `pytest tests/` to confirm 87/87 software tests pass on Ubuntu.
6. Run `scripts/diagnose_piper.sh` (strictly read-only CAN listening).
7. Run `scripts/diagnose_pika.sh` (strictly read-only USB & calibration audit).
8. Generate and review deployment report before proceeding to physical verification gates.
