# JARVIS-PiPER: Known Risks & Mitigation Protocols

**Audit Date:** October 2026  
**Scope:** Single-Arm Supervised Operation (AgileX PiPER 6-DOF)

---

## 1. Hardware & Physical Safety Risks

### Risk 1.1: High Actuator Torque Hazard ($30\,\text{N}\cdot\text{m}$)
- **Severity:** High
- **Description:** The Piper shoulder (`joint2`) and elbow (`joint3`) motors deliver up to $30\,\text{N}\cdot\text{m}$ peak torque. Rapid uncommanded motions can cause injury or damage equipment.
- **Mitigation:**
  - Slew-rate velocity limit enforced at $1.5\,\text{rad/s}$ in software (`SafetySupervisor`).
  - Physical 1-meter exclusion zone around robot arm during initial tests.
  - Emergency stop button must remain within operator reach at all times.

### Risk 1.2: Workspace Boundary Breach & Table Collision
- **Severity:** High
- **Description:** Driving the end-effector below table surface or outside reachable radius causes motor stall, thermal overload, or mechanical bending.
- **Mitigation:**
  - Strict Cartesian bounding box:
    $$x \in [0.10, 0.60]\,\text{m},\quad y \in [-0.45, 0.45]\,\text{m},\quad z \in [0.015, 0.55]\,\text{m}$$
  - Commands violating boundaries trigger an immediate E-Stop latch and command zero velocity.

### Risk 1.3: Unconnected Hardware & False Homing Assumptions
- **Severity:** Medium
- **Description:** Attempting to command hardware that is disconnected or powered off can lead to undefined states if mock software silently masks missing connections.
- **Mitigation:**
  - Zero silent fallbacks: `HARDWARE` mode strictly checks `/sys/class/net/can0`. If down, returns `BLOCKED_HARDWARE` and aborts immediately.
  - Zero-torque passive homing verification required before running autonomous policies.

---

## 2. Sensor & Perception Risks

### Risk 2.1: Optical Tracking Interference on PIKA Sense
- **Severity:** Medium
- **Description:** Direct sunlight, mirrors, or external IR emitters degrade HTC Vive Lighthouse v2.0 photodiode synchronization, causing tracking jitter or teleportation deltas.
- **Mitigation:**
  - 2nd-order Butterworth low-pass filter ($f_c = 12\,\text{Hz}$) attenuates high-frequency noise.
  - Step delta clamping: any single-step teleoperation displacement exceeding $0.05\,\text{m}$ latches a dead-man safety halt.

### Risk 2.2: USB 3.0 Bus Bandwidth Contention
- **Severity:** Medium
- **Description:** Running high-throughput 16-bit depth streams (30 FPS) alongside USB-to-CAN converters on a shared USB root hub causes packet latency and CAN frame drops.
- **Mitigation:**
  - Dedicate high-speed USB 3.0 root hub to camera; use separate USB 2.0/3.0 port for CAN adapter.
  - Time synchronizer logs maximum latency and aborts recording if slop exceeds $25\,\text{ms}$.

---

## 3. Autonomous Execution & LLM Risks

### Risk 3.1: Arbitrary Command Injection via Natural Language
- **Severity:** Critical
- **Description:** A language model directly outputting motor commands or running shell scripts could bypass safety bounds.
- **Mitigation:**
  - Language parser outputs **only** validated high-level skill tokens (`PickAndPlaceTask`, `TrajectoryPlayback`, `SystemDiagnostics`).
  - Motor trajectories are generated deterministically by the controller and verified by the independent `SafetySupervisor`. The LLM has zero direct motor publishing access.
