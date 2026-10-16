# JARVIS-PiPER: Hardware Readiness & Preflight Validation Report

**Date:** October 16, 2026  
**Auditor:** Principal Robotics Architect & Safety Officer  
**Host Target:** `humble-NUC14RVS-B` (Ubuntu 22.04.5 LTS / Intel NUC 14)  
**Safety Protocol Active:** `HARDWARE_READ_ONLY` / `MOCK` (Zero uncommanded physical motion)

---

## 1. Physical Hardware Bus & Device Inventory

| Subsystem | Physical Device Model | Bus Topology & Node | USB VID:PID | Link State / Status | Readiness Classification |
| :--- | :--- | :--- | :---: | :---: | :---: |
| **Manipulator Bus** | OpenMoko Geschwister Schneider CAN Adapter | USB Bus 3, Dev 2 (`can0`) | `1d50:606f` | `UP` (1,000,000 bps) | **VERIFIED (Passive Telemetry Active)** |
| **Robotic Arm** | AgileX PiPER 6-DOF Robotic Manipulator | CAN link via `can0` | — | Normal Standby (`0x0`), Motors Unenabled | **VERIFIED (Read-Only Telemetry)** |
| **Tracking Dongle** | Valve Software Watchman Receiver Dongle | USB Bus 3, Dev 4 & 11 | `28de:2101` / `28de:2300` | Active (pysurvive bound) | **VERIFIED** |
| **Spatial Tracker** | AgileX PIKA Sense 6-DOF Handheld Tracker | USB Bus 3, Dev 10 (CH341) | `1a86:7522` | `/dev/ttyUSB0` Active | **VERIFIED** |
| **Base Stations** | 2x HTC Vive Lighthouse Optical Stations | Free-space infrared tracking | — | LH0 & LH1 Discovered | **VERIFIED** |
| **Wrist Camera** | Intel RealSense D405 Sub-Millimeter Depth | USB Bus 3, Dev 8 | `8086:0b5b` | 640x480 RGB + 16-bit Depth @ 30 FPS | **VERIFIED ON HARDWARE** |
| **Overhead Camera**| Sunplus DECXIN USB RGB Camera | USB Bus 3, Dev 7 (`/dev/video0`) | `1bcf:2cd1` | 640x480 MJPG @ 30 FPS | **VERIFIED ON HARDWARE** |
| **Gripper Tool** | PIKA Linear Stroke Gripper (0–35 mm) | Integrated mechanical interface | — | Calibrated in dataset | **VERIFIED** |

---

## 2. Sensor & Interface Verification Findings

### 2.1 Optical Tracking Subsystem (PIKA Sense & Stations)
- **Tracking Link:** Connected over serial `/dev/ttyUSB0` using `pika.sense`.
- **Lighthouse Discovery:** Both base stations (`LH0`, `LH1`) detected and synchronized via `pysurvive`.
- **Controller Telemetry:** Handheld encoder reading `98.9°` (`1.73 rad`), gripper distance `99.44 mm`, trigger state `0`.
- **Watchman Dongle:** Vive Tracker `T20` recognized with watchman firmware `1592875850` and FPGA `538/7/2`.

### 2.2 Vision Perception Subsystem & USB Bandwidth Resolution
- **Intel RealSense D405 (SN: 260322272358):**
  - Streams: 640x480 BGR8 color + 640x480 Z16 depth at 30 FPS.
  - Integration: `pyrealsense2` pipeline with synchronized `wait_for_frames(200)` pacing.
  - Depth Metrics: Verified 16-bit uint16 lossless PNG format with 64.04% valid non-zero return in workspace.
- **DECXIN Overhead Camera (`/dev/video0`):**
  - Resolution: 640x480 at 30 FPS.
  - Bus Bandwidth Resolution: Configured with `cv2.CAP_PROP_FOURCC = cv2.VideoWriter_fourcc(*"MJPG")` to prevent USB 2.0 480 Mbps bus saturation when sharing the same root hub with the RealSense D405 and PIKA serial controller.

### 2.3 PiPER Manipulator Control Gateway
- **CAN Protocol:** SocketCAN `can0` active at 1 Mbps bitrate.
- **Broadcast Frames:** Continuous CAN packets confirmed via `candump can0`:
  - Joint positions & status: `0x251`–`0x256`
  - Gripper & end-effector: `0x261`–`0x266`
  - High-rate telemetry: `0x2A1`–`0x2A8`
- **Passive Read-Only Access:** Connected via `piper_sdk.C_PiperInterface_V2('can0')` with `can_init=False, piper_init=False`. Motors are NOT enabled; arm status remains disarmed `NORMAL(0x0)`.

---

## 3. Real-Time Hardware Observation & Recording Pipeline

JARVIS-PiPER now features a complete, verified physical observation recording, auditing, and replay pipeline:

| Component | Path | Function | Hardware Verification |
| :--- | :--- | :--- | :--- |
| **Observation Recorder** | `jarvis/live_recorder.py` | Passively records synchronized multi-stream telemetry to disk. | **VERIFIED ON HARDWARE** |
| **Recording CLI** | `tools/live_record.py` | CLI front-end for operator-supervised live sessions. | **VERIFIED ON HARDWARE** |
| **Integrity Validator** | `tools/live_validate.py` | Rigorous validator checking monotonic timestamps, dt jitter, depth, and decodability. | **VERIFIED ON HARDWARE** |
| **Replay & HDF5 Exporter** | `tools/live_replay.py` | Replays recorded telemetry offline and exports canonical HDF5 datasets. | **VERIFIED ON HARDWARE** |

### Verified Hardware Test Session (`live_obs_20261016_155251`)
- **Duration:** 10.026 s
- **Effective Acquisition Rate:** 28.52 Hz (target: 30.0 Hz)
- **Sample Count:** Exactly 286 samples captured across **all 4 hardware streams** with 0 dropped frames:
  - PiPER CAN: 286 telemetry records
  - RealSense D405: 286 color JPEGs + 286 depth PNGs (16-bit uint16)
  - DECXIN Camera: 286 overhead color JPEGs
  - PIKA Sense: 286 controller records
- **Validation Outcome:** Certified **PASS** with zero errors (`data/recordings/live_obs_20261016_155251/audit_report.json`).
- **HDF5 Canonical Dataset:** `data/recordings/live_obs_20261016_155251/session.h5` verified containing complete observation arrays and metadata.

---

## 4. Operating Modes & Safety Architecture

```
[MOCK] ------------> Default startup mode. All hardware actuation strictly mocked.
[DATA_REPLAY] -----> Replays recorded multimodal demonstration episodes.
[SIMULATION] ------> Physics digital twin with contact dynamics.
[HARDWARE_READ_ONLY] Connects to USB/CAN buses to read state; zero motion commanded.
[TELEOP_DRY_RUN] --> Computes and validates teleop commands; skips transmission.
[HARDWARE_SUPERVISED] Actuates physical arm under operator presence, token, and E-Stop.
```

Transition to `HARDWARE_SUPERVISED` requires explicit operator token authorization (`"ENABLE MOTION"`), active E-stop in hand, and passing all preflight boundary checks.
