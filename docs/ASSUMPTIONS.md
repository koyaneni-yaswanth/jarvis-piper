# JARVIS-PiPER System Assumptions & Kinematic Specification

**Status:** Verified Engineering Baseline  

---

## 1. Kinematic & Geometric Assumptions

### 1.1 AgileX PiPER S-V1.6-3 Denavit-Hartenberg (DH) Parameters
The forward and inverse kinematics models implemented in `jarvis.kinematics` assume standard modified DH conventions derived from official AgileX PiPER engineering specifications:

| Link $i$ | $\theta_i$ (Joint Variable) | $d_i$ (Link Offset, m) | $a_{i-1}$ (Link Length, m) | $\alpha_{i-1}$ (Link Twist, rad) |
| :---: | :---: | :---: | :---: | :---: |
| **1** | $q_1$ | $0.1230$ | $0.0000$ | $0.0000$ |
| **2** | $q_2$ | $0.0000$ | $0.0000$ | $+\pi/2$ |
| **3** | $q_3$ | $0.0000$ | $0.2600$ | $0.0000$ |
| **4** | $q_4$ | $0.2400$ | $0.0000$ | $+\pi/2$ |
| **5** | $q_5$ | $0.0000$ | $0.0000$ | $-\pi/2$ |
| **6** | $q_6$ | $0.1350$ | $0.0000$ | $+\pi/2$ |

*Total Spherical Reach:* $0.626\,\text{m}$ (Flange center).

### 1.2 Joint Coordinate Frame Conventions & Limits
- **Joint 1 (Base Yaw):** Rotation about vertical $Z$-axis. Range: $[-2.618, +2.618]\,\text{rad}$ ($[-150^\circ, +150^\circ]$).
- **Joint 2 (Shoulder Pitch):** Elevation angle. Range: $[0.000, +3.141]\,\text{rad}$ ($[0^\circ, +180^\circ]$).
- **Joint 3 (Elbow Pitch):** Forearm flexure. **CRITICAL:** Coordinate limits are strictly $[-2.967, 0.000]\,\text{rad}$ ($[-170^\circ, 0^\circ]$). Positive joint values correspond to impossible mechanical self-collision.
- **Joint 4 (Forearm Roll):** Range: $[-1.745, +1.745]\,\text{rad}$ ($[-100^\circ, +100^\circ]$).
- **Joint 5 (Wrist Pitch):** Range: $[-1.222, +1.222]\,\text{rad}$ ($[-70^\circ, +70^\circ]$).
- **Joint 6 (Wrist Roll):** Tool flange rotation. Range: $[-2.094, +2.094]\,\text{rad}$ ($[-120^\circ, +120^\circ]$).

---

## 2. End-Effector & Tool Assumptions

- **Type:** Bilateral parallel two-finger gripper.
- **Actuation Range:** $0.000\,\text{m}$ (fully closed) to $0.035\,\text{m}$ (fully open, $35\,\text{mm}$ stroke).
- **Maximum Grip Force:** $10.0\,\text{N}$ nominal (software limit applied to prevent deformation of delicate manipulation objects).
- **Tool Center Point (TCP) Offset:** End-effector fingertip center is located $+0.045\,\text{m}$ along tool flange $Z$-axis.

---

## 3. Communication & Bus Protocols

- **CAN Interface:** SocketCAN Linux protocol 2.0B.
  - Bitrate: $1,000,000\,\text{bps}$ ($1\,\text{Mbps}$).
  - Transmit Frequency: $20\text{--}50\,\text{Hz}$ command stream.
  - Telemetry Feedback: $50\text{--}100\,\text{Hz}$ broadcast from arm internal DSP.
- **Spatial Teleoperation:** AgileX PIKA Sense communicating over SteamVR 2.4 GHz protocol to USB Dongle (VID `0x28de`, PID `0x2101`).
  - Packet Rate: $\ge 60\,\text{Hz}$.
  - Latency: $\le 15\,\text{ms}$.
  - Tracking Freshness Threshold: $50\,\text{ms}$. If age exceeds $50\,\text{ms}$, tracking is marked LOST.

---

## 4. Mechanical & Electrical Rigidity

- The PiPER base is bolted securely to a level table ($> 25\,\text{mm}$ thick hardwood or aluminum extrusion) with 4x M6 bolts.
- Workspace contains a minimum $1.0\,\text{m}$ unobstructed sphere around arm base.
- Regulated 24V DC / 10A power supply with inline physical red mushroom E-stop button within arm's reach of operator.
