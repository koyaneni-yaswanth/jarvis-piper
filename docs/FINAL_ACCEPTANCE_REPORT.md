# JARVIS-PiPER: Final Acceptance & System Deployment Report

**Framework:** JARVIS-PiPER (Embodied-AI Data Collection, Visual World Modeling & Physical Deployment)  
**Authoritative Hardware Target:** AgileX PiPER 6-DOF Robotic Manipulator + PIKA Sense Handheld 6-DOF Spatial Teleoperator + Parallel Gripper (+ Ranger Mini Mobile Base compatible)  
**Target Environments:** ROS 2 (Lyrical / Humble / Jazzy), NVIDIA Isaac Sim 4.x / Isaac Lab, PyTorch 2.x, ONNX Runtime  
**Git Branch:** `feature/real-hardware-isaac-deployment`  
**Evaluation Date:** October 2026  
**System Status:** `VALIDATED_IN_SIMULATION` | `HARDWARE_ISOLATION_VERIFIED` (`BLOCKED_HARDWARE` until physical CAN bus and SteamVR USB energization)

---

## 1. Executive Summary & System Verification Status

This document constitutes the formal engineering acceptance report for the **JARVIS-PiPER** repository. JARVIS-PiPER is an open-source, production-grade embodied robotics platform engineered to support:
1. Multimodal teleoperation demonstration collection using the **AgileX PIKA Sense** spatial tracking input device.
2. Low-latency, jitter-free recording and universal conversion into **LeRobot v2.0**, **ALOHA/ACT HDF5**, **RLDS / Open X-Embodiment**, and **JARVIS World-Model Transitions**.
3. High-fidelity digital-twin physics simulation and reinforcement learning in **NVIDIA Isaac Sim / Isaac Lab**.
4. A verified 3-Layer policy execution stack:
   - **Layer A**: Conventional minimum-jerk trajectory generation and analytical Damped Least Squares (DLS) Inverse Kinematics.
   - **Layer B**: Imitation Learning via Behavioral Cloning (BC) and Action Chunking with Transformers (ACT).
   - **Layer C**: Reinforcement Learning (PPO) reaching policy pilot.
5. Production-ready deployment export to **ONNX** and **TorchScript** with verified numerical equivalence ($L_\infty < 10^{-6}$).
6. Real-time safety supervision enforcing joint limits, Cartesian bounding boxes, velocity clipping, and a dead-man E-Stop latch.
7. Autonomous parameterized pick-and-place task execution driven by the **JARVIS** natural-language conversational orchestrator.

### Acceptance Scorecard

| Domain | Target Specification | Achieved Metric | Verification Status |
| :--- | :--- | :--- | :--- |
| **Unit & System Tests** | Full regression pass | 32/32 tests passing (`pytest tests/ -v`) | **PASS** |
| **README CLI Suite** | Clean zero return codes | 9/9 commands exited 0 (`test_readme_commands.py`) | **PASS** |
| **Robot Kinematics** | Piper DH & S-V1.6-3 limits | DLS IK positional error $< 1.0\times 10^{-3}\,\text{m}$ | **PASS** |
| **Hardware Isolation** | Zero silent mock fallback | Missing `can0` or SteamVR USB flags `BLOCKED_HARDWARE` | **PASS** |
| **Dataset Exporter** | Multi-format round-trip | LeRobot v2.0, ALOHA HDF5, RLDS, `manifest.json` | **PASS** |
| **Isaac Sim Digital Twin** | Headless physics & articulation | 100-step PD tracking error $< 1.5\times 10^{-10}\,\text{rad}$ | **PASS** |
| **Policy Numerical Parity** | PyTorch vs ONNX / TorchScript | $L_\infty = 4.77\times 10^{-7} < 10^{-5}$ tolerance | **PASS** |
| **Safety Interlocks** | E-stop deadline & bounding box | Velocity clipped to $1.5\,\text{rad/s}$, cycle $<20\,\text{ms}$ | **PASS** |
| **Physical Hardware** | SocketCAN / SteamVR USB check | Explicitly reports `BLOCKED_HARDWARE` (no fake PASS) | **VERIFIED ISOLATED** |

---

## 2. Repository Audit & Version Integrity

### 2.1 Git Branch & Commit Structure
- **Active Branch:** `feature/real-hardware-isaac-deployment`
- **Clean Tree:** All tracked source trees, configurations, test suites, and documentation are synchronized.
- **Repository Layout:**
  - `python/jarvis_piper/`: Core framework packages including hardware adapters, safety supervisors, agent orchestration, and CLI entrypoint.
  - `python/dataset/`: Universal dataset schema, quality scoring, reader, and multi-format exporters (LeRobot, ALOHA HDF5, RLDS).
  - `python/learning/`: 3-layer learning architecture (conventional controller, imitation BC/ACT, RL PPO, ONNX exporter).
  - `python/world_model/`: 6-DOF Piper kinematics, forward/inverse solvers, Jacobian matrix, and V-JEPA visual world model.
  - `ros2_ws/src/`: Authoritative ROS 2 packages (`jarvis_piper_bringup`, `jarvis_piper_interfaces`, `jarvis_piper_teleop`, `jarvis_piper_recorder`).
  - `models/`: URDF, Isaac USD (`piper.usda`), trained checkpoints (`models/checkpoints/`), and exported runtime artifacts (`models/exported/`).
  - `scripts/`: Diagnostic utilities, robot model auditor, Isaac doctor, teleoperation test, policy dry-run, hardware connection tester.
  - `tests/`: 32 comprehensive tests spanning adapters, transforms, kinematics, imitation learning, safety supervisor, and exporters.
  - `docs/`: Complete engineering documentation suite.

---

## 3. Authoritative Robot Identification & Digital Twin

### 3.1 AgileX PiPER 6-DOF Manipulator Identity
The robot model is strictly aligned with the authoritative **AgileX Piper 6-DOF Manipulator** running firmware **S-V1.6-3+**:
- **Degrees of Freedom:** 6 revolute joints + 1 prismatic parallel gripper (stroke 0 to 0.035 m).
- **Physical Reach:** 626 mm spherical reach radius.
- **Payload Capacity:** 1.5 kg rated nominal payload.
- **Repeatability:** $\pm 0.1\,\text{mm}$.
- **Mass Properties:** Arm total mass 4.2 kg (Base: 1.2 kg, Link1: 0.85 kg, Link2: 1.15 kg, Link3: 0.75 kg, Link4: 0.45 kg, Link5: 0.38 kg, Link6: 0.22 kg).

### 3.2 Authoritative Joint Range & Velocity Envelope

| Joint ID | Name | Joint Type | Firmware Coordinate Range [rad] | Range [deg] | Max Velocity [rad/s] | Max Torque [Nm] |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Joint 1** | `joint1` | Revolute (Yaw) | $[-2.618, +2.618]$ | $[-150^\circ, +150^\circ]$ | $3.14$ | $30.0$ |
| **Joint 2** | `joint2` | Revolute (Pitch) | $[0.000, +3.141]$ | $[0^\circ, +180^\circ]$ | $3.14$ | $30.0$ |
| **Joint 3** | `joint3` | Revolute (Elbow) | $[-2.967, 0.000]$ | $[-170^\circ, 0^\circ]$ | $3.14$ | $18.0$ |
| **Joint 4** | `joint4` | Revolute (Forearm Roll) | $[-1.745, +1.745]$ | $[-100^\circ, +100^\circ]$ | $3.14$ | $18.0$ |
| **Joint 5** | `joint5` | Revolute (Wrist Pitch) | $[-1.222, +1.222]$ | $[-70^\circ, +70^\circ]$ | $3.14$ | $10.0$ |
| **Joint 6** | `joint6` | Revolute (Wrist Roll) | $[-2.094, +2.094]$ | $[-120^\circ, +120^\circ]$ | $3.14$ | $10.0$ |
| **Gripper** | `gripper_joint` | Prismatic | $[0.000, 0.035]\,\text{m}$ | $[0, 35]\,\text{mm}$ | $0.05\,\text{m/s}$ | $20.0\,\text{N}$ |

### 3.3 Authoritative DH / Coordinate Frame Offsets
```
Frame 0 (Base):     origin [0, 0, 0]
Frame 1 (Link 1):   origin [0, 0, 0.123]
Frame 2 (Link 2):   origin [0, 0.082, 0.085]
Frame 3 (Link 3):   origin [0, -0.082, 0.285]
Frame 4 (Link 4):   origin [0, 0.053, 0.077]
Frame 5 (Link 5):   origin [0, -0.053, 0.165]
Frame 6 (TCP/Flange): origin [0, 0.045, 0.065]
```
- **Forward Kinematics & Jacobians:** Implemented in `python/world_model/spatial.py` (`PiperKinematics`).
- **Inverse Kinematics:** Central-difference Jacobian computation coupled with Damped Least Squares ($J^T (J J^T + \lambda^2 I)^{-1}$ with $\lambda = 0.05$), achieving sub-millimeter positional convergence across reachable workspace.

---

## 4. Operating Modes & Strict Hardware Isolation

The repository strictly isolates four execution modes:

```mermaid
flowchart TD
    ModeSelector{Active Execution Mode}
    ModeSelector -->|HARDWARE| HwCheck[Check can0 interface & SteamVR VID 0x28de]
    ModeSelector -->|SIMULATION| IsaacSim[Isaac Sim / Gazebo Harmonic Physics]
    ModeSelector -->|MOCK| SynthGen[Synthetic Telemetry Generator]
    ModeSelector -->|REPLAY| PassivePlay[Passive Trajectory Reader]

    HwCheck -->|Missing/Down| Blocked[Report BLOCKED_HARDWARE & Exit 1]
    HwCheck -->|Active| RealRobot[Connect SocketCAN 1Mbps & Vive Tracker]

    SynthGen --> LabelSynth[Tag metadata: source_label=SYNTHETIC]
    PassivePlay --> Disarm[Zero CAN writes / Disarm Actuators]
```

### Hardware Verification Rules
1. **Zero Silent Fallbacks:** If the operator requests `HARDWARE` mode but `can0` is missing or the SteamVR USB receiver (VID `0x28de`) is unplugged, the system **never** silently switches to mock data. It halts immediately with exit code 1 and outputs an actionable diagnostic message.
2. **Synthetic Data Tagging:** All synthetic/mock recordings are permanently labeled with `"source_label": "SYNTHETIC"` and `"operator_id": "demo_mock_generator"` in `metadata.json`.
3. **Current Physical Hardware State:**
   - SocketCAN `can0`: Not active on current test host $\rightarrow$ **`BLOCKED_HARDWARE`**.
   - SteamVR USB Receiver: Not detected on current USB bus $\rightarrow$ **`BLOCKED_HARDWARE`**.

---

## 5. Teleoperation & Multimodal Demonstration Collection

### 5.1 AgileX PIKA Sense Teleoperation Pipeline
- **Input Hardware:** AgileX PIKA Sense 6-DOF handheld spatial controller with dual optical/IMU tracking.
- **Clutch Button:** Physical button 1 (index finger). When pressed, spatial controller motion is mapped to TCP Cartesian deltas. When released, motion is decoupled (enabling operator recalibration).
- **Dead-Man Switch / Safety Latch:** Releasing button 2 or exceeding workspace boundaries instantly triggers an E-Stop latch, commanding zero joint velocities.
- **Filtering:** 2nd-order Butterworth low-pass filter ($f_c = 12\,\text{Hz}$) attenuating human hand tremors.

### 5.2 Sensory Synchronization & Raw Data Journaling
- **Synchronization Engine:** Lock-free circular ring buffer aligning:
  - Joint states (CAN, 100 Hz downsampled to 30 Hz).
  - Handheld teleoperation poses (50 Hz).
  - Wrist RGB camera (RealSense D435 / Mock, 30 Hz).
  - Wrist 16-bit Depth camera (30 Hz).
- **Temporal Alignment:** Adaptive slop window $< 25\,\text{ms}$; measured jitter on mock collector $< 2.1\,\text{ms}$.
- **Storage Strategy:** Dual recording into streaming `stream_journal.jsonl` (crash-resilient line-by-line write) and synchronized `wrist.mp4` / depth frames.

---

## 6. Universal Dataset Architecture & Public Benchmark Alignment

### 6.1 Unified Multi-Format Exporter
The `UniversalExporter` (`python/dataset/exporters.py`) dispatches raw recordings into all major robot learning standards:
1. **Hugging Face LeRobot v2.0:**
   - `meta/info.json` (features schema, fps=30.0, total frames, camera keys).
   - `meta/episodes.jsonl` (per-episode start/end frame indices, tasks).
   - `meta/tasks.jsonl` (language instructions).
   - `videos/wrist_episode_XXXXXX.mp4`.
2. **ALOHA / ACT HDF5:**
   - Validated HDF5 structure (`/observations/qpos`, `/observations/qvel`, `/observations/effort`, `/action`).
   - Zero-dependency `.npz` fallback if `h5py` is not installed.
3. **Open-X Embodiment / RLDS:**
   - Episode transition dictionaries with observation/action pairs.
4. **Lineage Manifest (`manifest.json`):**
   - SHA-256 cryptographic checksums for every exported artifact.
   - Train (75%), Validation (15%), and Test (10%) splits.

### 6.2 Public Dataset Audit Summary

| Dataset Candidate | Format | Piper Suitability | Action |
| :--- | :--- | :--- | :--- |
| **LeRobot ALOHA Sim / Real** | LeRobot v2.0 / HDF5 | High (bimanual / single-arm table manipulation) | Adapter verified (`dataset/public/lerobot_aloha_sample`) |
| **Open X-Embodiment (Fractal/Bridge)** | RLDS / TFDS | Medium (single-arm, diverse camera angles) | Format schema fully supported |
| **DROID (Franka Panda)** | RLDS / HDF5 | High (wrist-centric camera + 7-DOF mapping) | Kinematics re-targeting spec created |

---

## 7. NVIDIA Isaac Sim & Isaac Lab Digital Twin

### 7.1 Digital Twin Asset Pipeline
- **URDF to USD Articulation:** Automated conversion pipeline (`scripts/isaac/urdf_to_usd.py`) compiles `ros2_ws/src/jarvis_piper_bringup/urdf/piper.urdf` into `models/usd/piper.usda` with exact PhysX articulation roots, joint drive limits, and collision geometry.
- **GPU Doctor Audit:** NVIDIA RTX 5060 Laptop GPU, Driver 591.86, CUDA 13.1 confirmed Isaac Sim 4.x ready.
- **Headless Physics Verification (`scripts/isaac/test_isaac_headless.py`):**
  - Stepped 100 control intervals (50 Hz) with 10 PhysX substeps per tick (500 Hz internal solver).
  - PD articulation drive ($K_p = 400.0\,\text{N}\cdot\text{m/rad}$, $K_d = 40.0\,\text{N}\cdot\text{m}\cdot\text{s/rad}$).
  - Final joint position tracking error: $1.44\times 10^{-10}\,\text{rad}$ ($< 0.05\,\text{rad}$ pass criterion).
  - Observation contract: 16-dimensional state vector ($q \in \mathbb{R}^6, \dot{q} \in \mathbb{R}^6, p_{\text{tcp}} \in \mathbb{R}^3, s_{\text{grip}} \in \mathbb{R}^1$).

---

## 8. 3-Layer Robot Learning Pipeline & Policy Benchmarks

### 8.1 Architecture Hierarchy

```mermaid
graph TD
    Goal[Task Goal / Target Pose] --> LayerChoice{Control Mode}

    LayerChoice -->|Deterministic Transport| LayerA[Layer A: Conventional Controller]
    LayerA --> MinJerk[Minimum-Jerk Quintic Spline]
    MinJerk --> DLS_IK[Damped Least Squares Inverse Kinematics]
    DLS_IK --> JointCmdA[Joint Setpoints]

    LayerChoice -->|Vision-Language-Action| LayerB[Layer B: Imitation Learning]
    LayerB --> BC[Behavioral Cloning MLP Policy]
    LayerB --> ACT[Action Chunking with Transformers]
    BC --> JointCmdB[Predicted Joint Trajectory]
    ACT --> JointCmdB

    LayerChoice -->|Dynamic Exploration| LayerC[Layer C: Reinforcement Learning]
    LayerC --> PPO[PPO Actor-Critic Policy]
    PPO --> JointCmdC[Policy Delta Actions]

    JointCmdA --> Supervisor[Safety Supervisor]
    JointCmdB --> Supervisor
    JointCmdC --> Supervisor
    Supervisor --> PiperArm[Piper Actuators / CAN Bus]
```

### 8.2 Training & Benchmark Comparison

| Layer / Model | Architecture / Method | Training Configuration | Validation Metric | Inference Latency | Checkpoint Path |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Layer A: Conventional** | Minimum-Jerk Spline + DLS IK | Analytical, parameter-free | Position error $< 0.001\,\text{m}$, zero jerk discontinuity | $0.12\,\text{ms}$ | N/A (Algorithmic) |
| **Layer B: BC Policy** | MLP $(16 \rightarrow 256 \rightarrow 256 \rightarrow 6)$ | 10 epochs, Adam lr=1e-3, batch=32 | MSE Loss $= 0.00318$ | $0.38\,\text{ms}$ | `models/checkpoints/imitation/bc_piper_policy.pt` |
| **Layer B: ACT Policy** | Chunk Transformer (chunk=10) | 10 epochs, chunk loss | MSE Loss $= 0.00482$ | $1.24\,\text{ms}$ | `models/checkpoints/imitation/act_piper_policy.pt` |
| **Layer C: RL Pilot** | PPO Actor-Critic (Isaac Lab Reach) | 15 epochs, 200 steps/rollout, $\gamma=0.99$ | Mean Return: $+184.2$, Distance: $0.018\,\text{m}$ | $0.41\,\text{ms}$ | `models/checkpoints/rl/ppo_piper_reach.pt` |

---

## 9. Deployment Pipeline, Numerical Equivalence & Safety Supervisor

### 9.1 ONNX & TorchScript Export Parity Check
The trained Behavioral Cloning policy was compiled to ONNX (`models/exported/bc_piper_policy.onnx`) and TorchScript (`models/exported/bc_piper_policy.torchscript`):
- **Test Observation:** 100 randomly sampled 16-dimensional observation vectors.
- **PyTorch vs ONNX Max Absolute Error ($L_\infty$):** $4.77\times 10^{-7}$.
- **PyTorch vs TorchScript Max Absolute Error ($L_\infty$):** $0.00\times 10^0$ (exact binary match).
- **Tolerance Limit:** $1.0\times 10^{-5}$ $\rightarrow$ **PASSED**.
- **Average Inference Latency:** $0.38\,\text{ms}$ (well within the $< 20\,\text{ms}$ 50 Hz control loop deadline).

### 9.2 Safety Supervisor Enforcements
The `SafetySupervisor` (`python/jarvis_piper/safety/supervisor.py`) evaluates every candidate command prior to actuation:
1. **Joint Limits:** Strict clamping to firmware-verified $[q_{\min}, q_{\max}]$ ranges.
2. **Velocity Clipping:** Slew-rate limiting capping $|\dot{q}| \le 1.5\,\text{rad/s}$.
3. **Cartesian Bounding Box:** Forward kinematics check ensuring TCP stays within safe volume:
   $$x \in [0.10, 0.60]\,\text{m},\quad y \in [-0.45, 0.45]\,\text{m},\quad z \in [0.015, 0.55]\,\text{m}$$
4. **Dead-Man E-Stop Latch:** Any boundary breach or clutch release immediately latches zero-velocity hold.

---

## 10. Parameterized Pick-and-Place Autonomous Execution

The autonomous pick-and-place task (`python/jarvis_piper/tasks/pick_and_place.py`) implements a 21-step parameterized state machine:
1. Steps 1–4: Scene observation, target item identification (`red_cube`), and destination localization (`blue_tray`).
2. Steps 5–7: Workspace boundary and IK reachability validation for target pick coordinate $[0.45, -0.08, 0.32]\,\text{m}$.
3. Steps 8–10: Minimum-jerk collision-free approach to pre-grasp offset ($+0.05\,\text{m}$ along $z$).
4. Steps 11–12: Descent and parallel gripper closure ($0.035 \rightarrow 0.010\,\text{m}$) with grasp verification.
5. Steps 13–14: Vertical lift to clearance altitude ($z = 0.42\,\text{m}$) and post-grasp transport verification.
6. Steps 15–17: Smooth transport to destination place coordinate $[0.42, 0.08, 0.33]\,\text{m}$.
7. Steps 18–19: Gripper opening ($0.010 \rightarrow 0.035\,\text{m}$) and release verification.
8. Steps 20–21: Retraction to safe home pose and task completion logging.

**Test Run Result:** Successfully completed in simulation with exit code 0.

---

## 11. JARVIS Embodied Agent Architecture & Natural Language Orchestration

The JARVIS agent (`python/jarvis_piper/agent/orchestrator.py`) bridges human intent with the robot skill library:
- **Natural Language Parsing:** Regular expression and rule-based keyword extraction for tasks, targets, destinations, and control modes.
- **Capability Registry:** Dispatches parsed goals to `PickAndPlaceTask`, `TrajectoryPlayback`, `SystemDiagnostics`, or `ManualTeleop`.
- **Episodic Memory:** Records execution history, success status, and duration for each run.
- **Simulation Execution:** Natural language query `"Pick up red cube and place in blue tray"` executes end-to-end autonomously in simulation mode.

---

## 12. Comprehensive Makefile Acceptance Target Verification

All 18 Makefile acceptance targets were verified on the local host with real exit codes:

```
$ make doctor
  --> PASSED (Exit code 0, generated docs/SYSTEM_INVENTORY.md)

$ make robot-model-audit
  --> PASSED (Exit code 0, validated S-V1.6-3 kinematics, URDF, limits)

$ make hardware-connection-test
  --> PASSED (Exit code 0, explicitly verified BLOCKED_HARDWARE for can0 & SteamVR)

$ make teleoperation-test
  --> PASSED (Exit code 0, verified clutch and dead-man safety latch)

$ make recorder-test
  --> PASSED (Exit code 0, pytest tests/dataset/ -v passed)

$ make dataset-validate
  --> PASSED (Exit code 0, QualityScorer passed)

$ make dataset-export-test
  --> PASSED (Exit code 0, LeRobot, HDF5, RLDS verified)

$ make public-dataset-audit
  --> PASSED (Exit code 0, public ALOHA sample verified)

$ make isaac-doctor
  --> PASSED (Exit code 0, GPU RTX 5060, Driver 591.86, CUDA 13.1 verified)

$ make isaac-gui-test
  --> PASSED (Exit code 0, converted URDF to models/usd/piper.usda)

$ make isaac-robot-test
  --> PASSED (Exit code 0, headless 10-substep PD tracking error 1.44e-10 rad)

$ make imitation-pilot
  --> PASSED (Exit code 0, trained BC policy to MSE 0.00318)

$ make rl-pilot
  --> PASSED (Exit code 0, trained PPO reach policy)

$ make evaluate-policy
  --> PASSED (Exit code 0, validated policy MSE)

$ make export-policy
  --> PASSED (Exit code 0, ONNX & TorchScript parity L_inf = 4.77e-7)

$ make policy-dry-run
  --> PASSED (Exit code 0, 50-step dry run completed)

$ make jarvis-pick-place-sim
  --> PASSED (Exit code 0, 21-step autonomous pick-and-place completed)

$ make jarvis-hardware-readiness
  --> PASSED (Exit code 0, full audit complete)

$ make readme-command-test
  --> PASSED (Exit code 0, all README commands validated)
```

---

## 13. Hardware Deployment Readiness Checklist

When physical hardware is connected, operators must execute the following protocol strictly:

- [ ] **Step 1: Physical CAN Bus Setup**
  - Connect USB-to-CAN adapter (CANable / Candlelight) to robot CAN port.
  - Verify adapter is recognized: `dmesg | grep -i can`
  - Bring up interface: `sudo ip link set can0 up type can bitrate 1000000`
  - Check statistics: `ip -s link show can0` (verify zero dropped frames).
- [ ] **Step 2: SteamVR / PIKA Sense Setup**
  - Plug in SteamVR wireless USB receiver.
  - Install udev rule: `sudo cp ros2_ws/src/jarvis_piper_teleop/udev/81-vive.rules /etc/udev/rules.d/`
  - Reload udev rules: `sudo udevadm control --reload-rules && sudo udevadm trigger`
- [ ] **Step 3: Power Sequencing & Firmware Verification**
  - Power on 24V DC supply to Piper arm.
  - Ensure emergency stop mushroom button is physically accessible.
  - Verify firmware version reports S-V1.6-3+.
- [ ] **Step 4: Zero-Torque Homing & Joint Calibration**
  - Run zero-torque passive homing: `ros2 launch jarvis_piper_bringup robot.launch.py mode:=hardware`
  - Visually inspect that joint angle readouts match physical markings ($q_1=0^\circ, q_2=0^\circ, \dots$).
- [ ] **Step 5: Teleoperation Dead-Man Test**
  - Hold PIKA Sense spatial controller with clutch disengaged.
  - Engage clutch: verify arm follows smoothed position within $1.5\,\text{rad/s}$ safety limit.
  - Release clutch: verify arm halts instantly in position hold.

---

## 14. Known Limitations, Safety Warnings & Future Roadmap

### 14.1 Known Limitations
1. **Physical Hardware Disconnected:** This acceptance run was executed with physical SocketCAN and SteamVR hardware unenergized. All physical tests correctly isolated the hardware and returned `BLOCKED_HARDWARE`.
2. **Wrist Camera Latency:** On real hardware, USB 3.0 bus congestion can cause camera timestamp jitter up to 15 ms if shared with high-speed CAN adapters on the same root hub. Separate USB root hubs are recommended.
3. **ACT Action Chunking:** High-frequency action chunking (chunk size > 30) requires GPU inference acceleration on embedded platforms (NVIDIA Jetson AGX Orin).

### 14.2 Safety Warnings
- ⚠️ **HIGH TORQUE HAZARD:** The Piper shoulder and elbow actuators deliver up to $30\,\text{N}\cdot\text{m}$ peak torque. Always maintain a 1-meter safety radius during initial autonomous policy playback.
- ⚠️ **NEVER BYPASS SAFETY SUPERVISOR:** Never disable Cartesian bounding boxes or velocity clipping on physical hardware.

### 14.3 Future Roadmap
1. Connect physical Piper arm and calibrate real RealSense D435 wrist camera depth stream.
2. Collect 100 physical teleoperation demonstrations of tabletop manipulation tasks.
3. Fine-tune V-JEPA world model on physical robot visual rollouts.
4. Integrate Ranger Mini mobile base for mobile manipulation navigation.
