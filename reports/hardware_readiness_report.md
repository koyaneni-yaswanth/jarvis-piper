# JARVIS-PiPER: Hardware Readiness & Preflight Validation Report

**Date:** October 15, 2026  
**Auditor:** Principal Robotics Architect & Safety Officer  
**Host Target:** `humble-NUC14RVS-B` (Ubuntu 22.04.5 LTS / Intel NUC 14)  
**Safety Protocol Active:** `HARDWARE_READ_ONLY` / `MOCK` (Zero uncommanded physical motion)

---

## 1. Physical Hardware Bus & Device Inventory

| Subsystem | Physical Device Model | Bus Topology & Node | USB VID:PID | Link State / Status | Readiness Classification |
| :--- | :--- | :--- | :---: | :---: | :---: |
| **Manipulator Bus** | OpenMoko Geschwister Schneider CAN Adapter | USB Bus 1, Dev 2 (`can0`) | `1d50:606f` | `DOWN` (1,000,000 bps) | **VERIFIED (Unactuated)** |
| **Robotic Arm** | AgileX PiPER 6-DOF Robotic Manipulator | CAN link via `can0` | — | Power Disarmed | **BLOCKED (Requires E-Stop Auth)** |
| **Tracking Dongle** | Valve Software Watchman Receiver Dongle | USB Bus 1, Dev 4 | `28de:2101` | Active | **VERIFIED** |
| **Spatial Tracker** | AgileX PIKA Sense 6-DOF Handheld Tracker | USB Bus 1, Dev 11 (LHR) | `28de:2300` | Active | **VERIFIED** |
| **Auxiliary Serial** | QinHeng CH341 USB-to-Serial Converter | `/dev/ttyUSB0` (`/dev/ttyUSB50`) | `1a86:7522` | Bound (dialout) | **VERIFIED** |
| **Base Stations** | 2x HTC Vive Lighthouse Optical Stations | Free-space infrared tracking | — | Operational in room | **VERIFIED** |
| **Wrist Camera** | Intel RealSense D405 Sub-Millimeter Depth | `/dev/video2`–`/dev/video7`, `media1` | `8086:0b5b` | Udev bound | **VERIFIED** |
| **Overhead Camera**| Sunplus DECXIN USB RGB Camera | `/dev/video0`, `/dev/video1` (`video50`) | `1bcf:2cd1` | Udev bound | **VERIFIED** |
| **Gripper Tool** | PIKA Linear Stroke Gripper (0–35 mm) | Integrated mechanical interface | — | Calibrated in dataset | **VERIFIED** |

---

## 2. Sensor & Interface Verification Findings

### 2.1 Optical Tracking Subsystem (PIKA Sense & Stations)
- **Tracking Frequency:** 160 Hz nominal pose stream verified in recorded episodes (`/pika/pose`).
- **Coordinate Conventions:** FLU (Forward-Left-Up) at tracker center.
- **Quaternion Verification:** Quaternions are stored as $[qx, qy, qz, qw]$ and maintain strict unit norm ($\|q\| = 1.0000 \pm 10^{-6}$).
- **Safety Interlocks:** Tracking age watchdog enforces disarm if pose freshness exceeds $50.0\,\text{ms}$. Identity transform rejection prevents uncalibrated base-station initialization.

### 2.2 Vision Perception Subsystem
- **Intel RealSense D405:**
  - Streams: Color RGB (640x480 @ 30 FPS) + Depth Z16 (640x480 @ 30 FPS).
  - Depth Scale: Queried from device metadata as $0.00009999999747378752\,\text{m/unit}$ ($100\,\mu\text{m}$ per count). Sub-millimeter near-field fidelity confirmed.
  - Saturated Pixels: Value `65535` strictly mapped to invalid/infinite background.
- **DECXIN Overhead Camera:**
  - Node: `/dev/video0` and `/dev/video1` (aliased to `/dev/video50` via udev rule).
  - Streams: 640x480 MJPG/YUYV @ 30 FPS wide-angle context view.

### 2.3 PiPER Manipulator Control Gateway
- **CAN Protocol:** SocketCAN `can0` configured for 1 Mbps (`bitrate 1000000`).
- **Motor Enable Gating:** S-V1.6-3 firmware requires explicit service call `piper_msgs/srv/Enable` with `enable_request = True`.
- **Current Bus State:** Interface `can0` is currently `DOWN`. Motor power remains disconnected.

---

## 3. Operating Modes & Enforcement Architecture

The system supports 6 distinct, mutually exclusive operational modes:

```
[MOCK] ------------> Default startup mode. All hardware actuation strictly mocked.
[DATA_REPLAY] -----> Replays recorded multimodal demonstration episodes.
[SIMULATION] ------> Physics digital twin with contact dynamics.
[HARDWARE_READ_ONLY] Connects to USB/CAN buses to read state; zero motion commanded.
[TELEOP_DRY_RUN] --> Computes and validates teleop commands; skips transmission.
[HARDWARE_SUPERVISED] Actuates physical arm under operator presence, token, and E-Stop.
```

Transition to `HARDWARE_SUPERVISED` is strictly prevented unless:
1. Operator token `"ENABLE MOTION"` is provided.
2. Hardware preflight diagnostics pass with zero critical errors.
3. The Independent Safety Supervisor confirms joint and workspace bounds.
4. An on-site human operator is present with physical emergency stop in hand.

---

## 4. Formal Physical Testing Approval Request (Per Safety Policy Rule 18)

Before the first physical movement of the AgileX PiPER arm can be initiated, the following test plan is submitted for explicit operator review and authorization:

### 4.1 Proposed Test Specification
- **Test Identifier:** `PHYSICAL-TEST-001-SUPERVISED-NUDGE`
- **Initial Robot State:** Arm stationary, clear of table and obstacles. Hand on physical E-stop.
- **Initial Joint Angles:** $\mathbf{q}_0 = [0.0, 0.5236, -0.5236, 0.0, 0.0, 0.0]\,\text{rad}$ (nominal home clearance pose).
- **Proposed Motion:** Low-risk, single-axis vertical Cartesian nudge: $\Delta Z = +0.020\,\text{m}$ (+20 mm) at conservative speed (10% of maximum speed rate, $\le 0.05\,\text{m/s}$).
- **Expected Duration:** 3.0 seconds total motion, followed by stationary hold.
- **Validated Safety Limits:**
  - Maximum Cartesian step: $\le 0.010\,\text{m}$ per control cycle.
  - Joint velocity limit: $\le 0.5\,\text{rad/s}$ (conservative preflight clamp).
  - Workspace Box: $X \in [0.10, 0.55]$, $Y \in [-0.35, 0.35]$, $Z \in [0.05, 0.50]\,\text{m}$.
- **Emergency Stop Procedure:**
  1. Primary: Operator depresses physical hardware emergency stop button on PiPER base.
  2. Secondary: Software watchdog drops CAN heartbeat on `Ctrl+C` or communication loss ($>100\,\text{ms}$), executing `piper.DisableArm(7)`.
- **Operator Required Actions to Authorize:**
  1. Confirm physical workspace is completely clear of personnel and unanchored tools.
  2. Confirm physical E-stop button is connected and held.
  3. Execute:
     ```bash
     sudo ip link set can0 type can bitrate 1000000
     sudo ip link set can0 up
     ```
  4. Run operator-supervised test command:
     ```bash
     python3 -m jarvis.cli policy --execute --steps 20
     ```

*Until the operator confirms readiness and brings up `can0`, all physical actuation remains locked in `MOCK` and `HARDWARE_READ_ONLY` mode.*
