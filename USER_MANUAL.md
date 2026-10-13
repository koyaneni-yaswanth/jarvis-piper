# JARVIS-PiPER: Official User Manual & Deployment Guide

> **Release Standard:** Deploy-anywhere embodied-AI teleoperation and imitation learning on the physical **AgileX PiPER 6-DOF Manipulator** and **PIKA Sense Teleoperation Hub**.

---

## 1. Overview & Safety Warnings (Read First)

⚠ **MANDATORY SAFETY RULES — NEVER OPERATE WITHOUT REVIEWING:**
1. **Motion Authorization Gate:** The robot controller will refuse any physical actuation unless the operator types `ENABLE MOTION` in the current session.
2. **Clear Workspace:** Maintain a minimum **$1.0\,\text{m}$ clearance radius** around the arm base free of obstacles, loose cables, and bystanders.
3. **Emergency Stop Access:** Always hold or position the physical 24V power cut-off / mushroom e-stop button within direct arm's reach.
4. **Dead-Man Clutch:** Physical arm movement occurs **ONLY** while the operator continuously holds Button 1 (dead-man clutch) on the PIKA Sense. Releasing the clutch immediately holds position.
5. **Never Leave Arm Unattended:** Never power or leave the manipulator active without an operator present.

---

## 2. What You Need

### 2.1 Hardware Bill of Materials
- **Manipulator:** AgileX PiPER 6-DOF Robotic Arm with bilateral parallel gripper (0 to 35 mm stroke).
- **Power Supply:** 24V DC / 10A regulated power adapter.
- **CAN Adapter:** USB-to-CAN adapter (CANable / Candlelight firmware, 1 Mbps bitrate).
- **Spatial Teleoperation Hub:** AgileX PIKA Sense + SteamVR Wireless Receiver USB Dongle (VID `0x28de`).
- **Base Stations:** 2x HTC Vive / Valve Lighthouse v2.0 tracking base stations on stable tripods ($>2.0\,\text{m}$ high, tilted 25°–35°).
- **Host PC:** Target Ubuntu 22.04 LTS x86_64 workstation with USB 3.0 ports.

### 2.2 Cabling & Power-On Sequence
1. Secure the PiPER arm base to a rigid table or workbench with 4x M6 bolts.
2. Connect CAN_H and CAN_L from the USB-to-CAN adapter to the PiPER base aviation connector.
3. Plug the USB-to-CAN adapter into a USB 3.0 port on the PC.
4. Plug the SteamVR wireless dongle into another USB port.
5. Energize the base stations (confirm green LEDs).
6. Power on the 24V DC supply to the PiPER arm.
7. Ensure the emergency stop mushroom button is released (rotate clockwise).

---

## 3. Installation

Clone the repository and run the idempotent installer:

```bash
git clone https://github.com/koyaneni-yaswanth/jarvis-piper.git
cd jarvis-piper

# 1. Standard non-destructive project install
./install.sh

# 2. Optional system configuration (udev rules, CAN setup, dialout group)
./install.sh --system
```

Verify your environment immediately:
```bash
python3 -m jarvis.cli doctor
```
*Expected Output:* All diagnostic rows report `[PASS]` or non-blocking `[WARN]`.

---

## 4. First-Time Setup & Device Detection

Generate a machine-specific configuration override (`config.local.yaml`):

```bash
python3 -c "from jarvis.doctor import JarvisDoctor; JarvisDoctor().print_report()"
```

Confirm that user permissions are established:
```bash
groups $USER | grep dialout
```
*If dialout is missing, run `sudo usermod -aG dialout $USER` and re-login.*

---

## 5. Read-Only Hardware Verification

Run non-destructive hardware checks without moving the arm:

### 5.1 Verify SocketCAN Telemetry
```bash
# Check SocketCAN interface state
ip -s link show can0
```
*Expected Output:* `state UP`, bitrate `1000000`, 0 drop errors.

### 5.2 Read Genuine Joint Encoders
```bash
python3 -c "
from jarvis.hardware import RealPiperArm
arm = RealPiperArm(can_interface='can0')
arm.connect()
print('Joint Angles (rad):', arm.get_joint_state()['positions'])
"
```
*Expected Output:* Prints 6 valid joint angles matching physical arm pose.

---

## 6. PIKA-to-PiPER Calibration

Calibrate optical tracking space to arm base coordinates:

```bash
# 1. Base station optical tag calibration
cd ~/pika_ros/install/pika_locator/lib && ./survive-cli --force-calibrate
```
*Wait until calibration error output is $< 0.005\,\text{m}$, then press Ctrl+C.*

---

## 7. Supervised Teleoperation

### 7.1 Pre-Flight Verification
```bash
# Verify all safety supervisor interlocks on mock data
pytest tests/unit/test_adapters.py -v
```

### 7.2 Supervised Teleoperation Execution
```bash
# Dry run first (validates signal streams without moving arm)
python3 -m jarvis.cli teleop --dry-run

# Hardware execution (requires operator confirmation token)
python3 -m jarvis.cli teleop --execute
```
*Hold Button 1 on PIKA Sense to move the robot arm. Release Button 1 to hold position.*

---

## 8. Recording Demonstrations

Collect validated demonstration episodes:

```bash
python3 -m jarvis.cli record --steps 60 --output-dir data/raw
```

Validate every recorded episode against the 7-point quality audit:
```bash
python3 -m jarvis.cli validate --dataset data/raw/episode_mock_001
```
*Expected Output:* `Valid: True`, `Errors: []`.

---

## 9. Training Behavioral Cloning (BC) Policy

Train a deterministic Behavioral Cloning policy:

```bash
python3 -m jarvis.cli train --epochs 20 --data-dir data/raw
```
*Expected Output:* `[OK] Training complete! Train loss: <0.05, Val loss: <0.06`.

---

## 10. Running the Supervised Policy

### 10.1 Dry Run Verification
```bash
python3 -m jarvis.cli policy --dry-run --steps 50
```
*Evaluates policy predictions and verifies that all actions stay inside joint and workspace limits.*

### 10.2 Supervised Real-Arm Rollout
```bash
python3 -m jarvis.cli policy --execute --steps 50
```
*Halts automatically if > 15 action jumps are clamped or tracking signal drops.*

---

## 11. Moving Data and Checkpoints Between Machines

To copy recorded demonstrations and model checkpoints from the hardware robot to your training laptop:

```bash
# Archive demonstrations on robot PC:
tar -czvf demonstrations.tar.gz data/raw/

# Copy checkpoint back to robot:
rsync -avz models/checkpoints/bc_piper_policy.pt user@robot-nuc:~/jarvis-piper/models/checkpoints/
```

---

## 12. Troubleshooting Table

| Symptom / Error | Likely Cause | Exact Fix Command | Manual Section |
| :--- | :--- | :--- | :---: |
| `CanInterfaceDownError` | USB-to-CAN unplugged or interface down | `sudo ip link set can0 up type can bitrate 1000000` | Section 3 |
| `DeviceNotFoundError` | SteamVR USB dongle unplugged or udev missing | `sudo cp ros2_ws/src/jarvis_piper_teleop/udev/81-vive.rules /etc/udev/rules.d/ && sudo udevadm control --reload-rules` | Section 2 & 3 |
| `TrackingLostError` | PIKA Sense obscured from base station FOV | Clear line of sight; recheck base station green LED | Section 6 & 7 |
| `ClutchReleasedError` | Button 1 not held during teleop command | Depress and hold dead-man clutch (Button 1) | Section 1 & 7 |
| `EStopTriggeredError` | Emergency stop software latch active | `jarvis reset-estop` with token `ENABLE MOTION` | Section 1 |
| `WorkspaceViolationError` | Target pose exceeds Cartesian boundary | Re-center teleop workspace origin | Section 6 & 13 |
| `WatchdogTimeoutError` | Command stream dropped for $> 100\,\text{ms}$ | Check network/CPU load; restart node | Section 7 |
| `PermissionDeniedError` | User missing from `dialout` group | `sudo usermod -aG dialout $USER` (re-login) | Section 3 |

---

## 13. Hardware Facts & Specifications

- **Degrees of Freedom:** 6 revolute arm joints + 1 prismatic bilateral gripper.
- **Physical Reach:** $626\,\text{mm}$ spherical reach.
- **Nominal Payload:** $1.5\,\text{kg}$.
- **Joint Boundaries (Radians):**
  - Joint 1 (Base Yaw): $[-2.618, +2.618]\,\text{rad}$ ($[-150^\circ, +150^\circ]$)
  - Joint 2 (Shoulder Pitch): $[0.000, +3.141]\,\text{rad}$ ($[0^\circ, +180^\circ]$)
  - Joint 3 (Elbow Pitch): $[-2.967, 0.000]\,\text{rad}$ ($[-170^\circ, 0^\circ]$)
  - Joint 4 (Forearm Roll): $[-1.745, +1.745]\,\text{rad}$ ($[-100^\circ, +100^\circ]$)
  - Joint 5 (Wrist Pitch): $[-1.222, +1.222]\,\text{rad}$ ($[-70^\circ, +70^\circ]$)
  - Joint 6 (Wrist Roll): $[-2.094, +2.094]\,\text{rad}$ ($[-120^\circ, +120^\circ]$)
  - Gripper Stroke: $[0.000, 0.035]\,\text{m}$ ($[0, 35]\,\text{mm}$)
- **Max Joint Velocity:** $3.14\,\text{rad/s}$ (Capped to $0.15\,\text{rad/s}$ during conservative bring-up).
- **Communication Protocol:** SocketCAN 2.0B at **1,000,000 baud (1 Mbps)**.

---

## 14. Update and Rollback

To update safely from GitHub:
```bash
git pull origin main
./install.sh
python3 -m jarvis.cli doctor
```

To roll back to a known stable release tag:
```bash
git checkout tags/v1.0.0
./install.sh
```
