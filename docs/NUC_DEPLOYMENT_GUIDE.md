# JARVIS-PiPER: GitHub-to-NUC Deployment & Real Hardware Verification Guide

> **MANDATORY SAFETY CONSTITUTION**  
> 1. Real robot physical actuation is **locked by default**. Every command defaults to `--dry-run`.  
> 2. Physical motor movement requires ALL of: operator presence, continuous dead-man clutch hold, unlatched E-stop, verified calibration, and the explicit runtime session token: `"ENABLE MOTION"`.  
> 3. If any gate fails or an unexpected noise/motion occurs, immediately hit the physical E-Stop or kill the process with `Ctrl+C`.

---

## 1. Prerequisites on Physical Intel NUC

| Component | Target Requirement | Verification Command |
| :--- | :--- | :--- |
| **Operating System** | Ubuntu 22.04 LTS (x86_64) | `cat /etc/os-release` |
| **ROS Distribution** | ROS 2 Humble Hawksbill | `echo $ROS_DISTRO` -> `humble` |
| **Python Environment**| System Python 3.10.12 (`/usr/bin/python3`) | `python3 --version` |
| **Conda Status** | Strictly DEACTIVATED | `which python3` must NOT contain `conda` |
| **User Groups** | `dialout` and `plugdev` | `groups` must show both |
| **CAN Hardware** | USB-to-CAN adapter plugged into USB 3.0 | `lsusb` |
| **Tracking Hardware**| SteamVR wireless dongle (VID `0x28de`) | `lsusb` |

---

## 2. GitHub-to-NUC Deployment Procedure

Execute these exact commands on the physical NUC:

### Step 1: Clone or Navigate to Repository
If cloning fresh:
```bash
git clone https://github.com/koyaneni-yaswanth/jarvis-piper.git ~/jarvis-piper
cd ~/jarvis-piper
```

If updating an existing checkout (safe, non-destructive sync):
```bash
cd ~/jarvis-piper

# 1. Inspect existing state and preserve any untracked or modified files
git status
git diff

# 2. Fetch origin without overwriting
git fetch origin main

# 3. Inspect incoming commits
git log HEAD..origin/main --oneline

# 4. Fast-forward to latest commit
git merge --ff-only origin/main
```

### Step 2: System Python & ROS 2 Environment Setup
To ensure ROS 2 binaries and system libraries resolve without collision:

```bash
# Deactivate conda if active in current shell
if command -v conda &>/dev/null; then
    conda deactivate 2>/dev/null || true
fi

# Source official ROS 2 Humble setup
source /opt/ros/humble/setup.bash

# Verify active Python is system Python 3.10
which python3
# Expected output: /usr/bin/python3
```

### Step 3: Install Core Dependencies Without `sudo pip`
Never use `sudo pip` or blindly overwrite system Python packages:

```bash
# Option A: Install JARVIS in user editable mode (Recommended for ROS 2 compatibility)
pip install --user -e .

# Option B: Install optional development tools (pytest)
pip install --user pytest pyyaml numpy
```

---

## 3. Physical Hardware Verification Gates

Never skip any gate. If any gate fails, stop immediately at that gate and consult the remediation instructions.

```
+-------------------------------------------------------------+
| Gate 1: Environment & System Preflight                     |
+-------------------------------------------------------------+
                              | PASS
+-------------------------------------------------------------+
| Gate 2: Device Enumeration & Link State (CAN & USB)         |
+-------------------------------------------------------------+
                              | PASS
+-------------------------------------------------------------+
| Gate 3: Passive Feedback Telemetry (Zero Motor Motion)     |
+-------------------------------------------------------------+
                              | PASS
+-------------------------------------------------------------+
| Gate 4: Optical Calibration & Tracking Validation           |
+-------------------------------------------------------------+
                              | PASS
+-------------------------------------------------------------+
| Gate 5: Supervised Dry-Run Loop (Mock/Software Gate)        |
+-------------------------------------------------------------+
                              | PASS & Operator "ENABLE MOTION"
+-------------------------------------------------------------+
| Gate 6: Supervised Physical Hardware Execution              |
+-------------------------------------------------------------+
```

---

### Gate 1: Environment & System Preflight

Run the bundled preflight audit:
```bash
./scripts/nuc_preflight.sh
```

**Pass Criteria:**
- Ubuntu 22.04 LTS confirmed.
- System Python 3.10 active.
- Zero Conda interference.
- User belongs to `dialout` and `plugdev`.
- Configuration schema valid (`python3 -m jarvis.cli validate-config` returns `Valid: True`).

---

### Gate 2: Device Enumeration & Link State

Verify that physical hardware is present on the system buses:

```bash
# 1. Bring up SocketCAN interface at 1,000,000 bps
sudo ip link set can0 down 2>/dev/null || true
sudo ip link set can0 type can bitrate 1000000
sudo ip link set can0 up

# 2. Verify link status
ip link show can0
# Expected: state UP

# 3. Check USB adapters
lsusb | grep -iE "can|candle|gs_usb|28de:|valve"
```

**Pass Criteria:**
- `can0` state is `UP` with bitrate `1000000`.
- USB CAN adapter enumerated.
- SteamVR wireless dongle (VID `0x28de`) enumerated.

---

### Gate 3: Passive Feedback Telemetry (Zero Motor Motion)

Run passive manipulator diagnostics:
```bash
./scripts/diagnose_piper.sh can0
```

Verify that genuine encoder telemetry frames are arriving without enabling motor power:
```bash
timeout 2s candump can0
```

**Pass Criteria:**
- Periodic feedback CAN frames `0x2A1` through `0x2A6` are received.
- Zero `0x159` motor enable frames transmitted.
- Encoder feedback decodes cleanly into 6 valid joint angles with freshness $< 100\,\text{ms}$.

---

### Gate 4: Optical Calibration & Tracking Validation

Run passive PIKA diagnostics:
```bash
./scripts/diagnose_pika.sh
```

Inspect libsurvive calibration state:
```bash
cat ~/.config/libsurvive/config.json
```

**Pass Criteria:**
- File exists with valid base station geometry (`LH_0`, `LH_1`).
- `TrackingValidator` confirms unit quaternions ($|\|q\| - 1| \le 0.05$) and telemetry freshness $\le 50\,\text{ms}$.
- If status is `NOT_CONFIGURED` or `NOT_CALIBRATED`, run `survive-cli --force-calibrate` while keeping PIKA Sense stationary on workbench.

---

### Gate 5: Supervised Dry-Run Loop

Execute software teleoperation dry-run:
```bash
python3 -m jarvis.cli teleop --dry-run --steps 50
```

**Pass Criteria:**
- Teleoperation mapper receives poses from PIKA Sense.
- Safety supervisor checks joint limits, workspace bounds, and clutch state.
- Physical arm **does not move**.
- Completed 50 steps without raising `JarvisError`.

---

### Gate 6: Supervised Physical Hardware Execution

> [!CAUTION]
> Hardware motion is permitted **only** when Gates 1–5 are completely verified, an emergency stop button is within operator hand reach, and the physical workspace is clear of obstructions.

Execute supervised teleoperation with explicit operator confirmation:
```bash
python3 -m jarvis.cli teleop --execute --steps 30
```
When prompted:
```text
Enter motion authorization token ('ENABLE MOTION'): ENABLE MOTION
```

**Pass Criteria:**
- Operator holds dead-man clutch button continuously during movement.
- Arm follows scaled PIKA Sense displacement smoothly at conservative 10% speed scale.
- Releasing clutch immediately freezes motion.
- Software latches E-stop and ceases command publishing on any tracking loss.

---

## 4. Post-Deployment Verification Report

Generate the official markdown deployment report:
```bash
./scripts/generate_deployment_report.sh
```

Inspect the generated report in `reports/` and archive it for milestone sign-off.

---

## 5. Troubleshooting & Recovery Runbook

| Symptom / Error | Root Cause | Exact Remedy Command |
| :--- | :--- | :--- |
| `CanInterfaceDownError` | `can0` down or USB cable unplugged | `sudo ip link set can0 up type can bitrate 1000000` |
| `PermissionError: /dev/ttyACM*` | User not in `dialout` group | `sudo usermod -aG dialout,plugdev $USER` (re-login) |
| `ImportError: rclpy` | Conda collision | `conda deactivate && source /opt/ros/humble/setup.bash` |
| `CalibrationStatusError` | libsurvive uncalibrated | `survive-cli --force-calibrate` |
| `StaleFeedbackError` | Arm power off or CAN bus disconnect | Power 24V supply to arm; verify 120 $\Omega$ termination resistor |
| `TrackingLostError` | Base station beam occluded | Re-position base stations for direct optical line-of-sight |
| `MotionNotAuthorizedError` | Incorrect session token typed | Type exact uppercase string: `ENABLE MOTION` |
