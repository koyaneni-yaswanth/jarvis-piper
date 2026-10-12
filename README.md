# JARVIS-PiPER

<div align="center">

# JARVIS-PiPER: An Open Embodied-AI Data Collection and Visual World Model Framework for PiPER Robotic Manipulation

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-green.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![PyTorch 2.x](https://img.shields.io/badge/PyTorch-2.x-red.svg)](https://pytorch.org/)
[![ROS 2 Ready](https://img.shields.io/badge/ROS_2-Lyrical%20%7C%20Humble%20%7C%20Jazzy-blue.svg)](https://docs.ros.org/)
[![NVIDIA Isaac Sim](https://img.shields.io/badge/NVIDIA-Isaac_Sim_4.x_%7C_Isaac_Lab-76B900.svg)](https://developer.nvidia.com/isaac-sim)
[![Tests Passing](https://img.shields.io/badge/Tests-32%20Passing-brightgreen.svg)](tests/)
[![Hardware Isolation](https://img.shields.io/badge/Hardware-Isolated%20(BLOCKED__HARDWARE)-orange.svg)](scripts/hardware_connection_test.py)

**A production-grade, research-ready platform for multimodal teleoperation demonstration collection, LeRobot/ALOHA/RLDS dataset engineering, Isaac Sim simulation, 3-layer robot learning, and JARVIS natural-language autonomous manipulation on the AgileX PiPER 6-DOF robotic arm.**

</div>

---

## Table of Contents
1. [Overview & Highlights](#1-overview--highlights)
2. [System Architecture](#2-system-architecture)
3. [Authoritative Robot & Hardware Specifications](#3-authoritative-robot--hardware-specifications)
4. [Software Matrix & Prerequisites](#4-software-matrix--prerequisites)
5. [Quickstart in 5 Minutes](#5-quickstart-in-5-minutes)
6. [CLI Reference (`jarvis-piper`)](#6-cli-reference-jarvis-piper)
7. [Teleoperation with AgileX PIKA Sense](#7-teleoperation-with-agilex-pika-sense)
8. [Universal Dataset Pipeline & Public Benchmarks](#8-universal-dataset-pipeline--public-benchmarks)
9. [NVIDIA Isaac Sim & Isaac Lab Integration](#9-nvidia-isaac-sim--isaac-lab-integration)
10. [3-Layer Robot Learning Pipeline](#10-3-layer-robot-learning-pipeline)
11. [Policy Export & Runtime Safety Supervisor](#11-policy-export--runtime-safety-supervisor)
12. [Autonomous Pick-and-Place & JARVIS Agent](#12-autonomous-pick-and-place--jarvis-agent)
13. [Makefile Acceptance Target Suite](#13-makefile-acceptance-target-suite)
14. [Physical Hardware Deployment Protocol](#14-physical-hardware-deployment-protocol)
15. [Troubleshooting & FAQ](#15-troubleshooting--faq)
16. [Citation & License](#16-citation--license)

---

## 1. Overview & Highlights

**JARVIS-PiPER** bridges the gap between low-level robot hardware control and modern embodied-AI research. Designed for the **AgileX PiPER 6-DOF Manipulator**, **PIKA Sense 6-DOF Teleoperation Hub**, and compatible with the **Ranger Mini Mobile Base**, it provides a complete end-to-end stack:

- **4 Strictly Isolated Operating Modes**:
  - `HARDWARE`: Direct SocketCAN 1 Mbps control and SteamVR 6-DOF tracking. No silent fallbacks—if hardware is absent, reports `BLOCKED_HARDWARE`.
  - `SIMULATION`: NVIDIA Isaac Sim / Isaac Lab and Gazebo physics digital twin.
  - `MOCK`: High-fidelity synthetic telemetry generator for zero-hardware CI and testing (labeled `SYNTHETIC`).
  - `REPLAY`: Passive, read-only playback of recorded datasets with zero motor actuation.
- **Universal Embodied-AI Dataset Exporters**: Instant conversion to Hugging Face **LeRobot v2.0**, **ALOHA / ACT HDF5**, **RLDS / Open X-Embodiment**, and cryptographic lineage manifest generation (`manifest.json`).
- **3-Layer Learning Pipeline**:
  - **Layer A**: Conventional minimum-jerk trajectory planner + Damped Least Squares Inverse Kinematics.
  - **Layer B**: Imitation Learning (Behavioral Cloning MLP and Action Chunking with Transformers).
  - **Layer C**: Reinforcement Learning (PPO reaching policy in simulated Isaac environment).
- **Deployment Ready**: PyTorch to **ONNX** and **TorchScript** compilation with verified numerical equivalence ($L_\infty < 10^{-6}$ error) and hard real-time **Safety Supervisor** bounding boxes and E-Stop latches.
- **JARVIS Natural-Language Orchestration**: Conversational intent parser and capability registry driving 21-step parameterized pick-and-place manipulation.

---

## 2. System Architecture

### 2.1 Multimodal Demonstration Collection & Learning Flow

```mermaid
flowchart TD
    subgraph Input ["1. Human Spatial Teleoperation"]
        PikaSense["AgileX PIKA Sense\n(6-DoF Tracker + Buttons)"]
        Clutch["Clutch Button\n(Dead-man switch)"]
    end

    subgraph Hardware ["2. Actuation & Sensory Bus"]
        CANBus["SocketCAN (can0)\n1 Mbps Bitrate"]
        PiperArm["AgileX PiPER 6-DOF\n+ Parallel Gripper"]
        Cameras["Wrist RGB-D Camera\n(30 FPS / 16-bit Depth)"]
    end

    subgraph Sync ["3. Multi-Modal Synchronization"]
        RingBuffer["Lock-Free Circular Ring Buffer\n(Slop window < 25ms)"]
        Journal["Crash-Resilient\nstream_journal.jsonl"]
    end

    subgraph DataOps ["4. Universal Dataset Pipeline"]
        Quality["Quality Assurance\n(7-point audit & scoring)"]
        LeRobot["HF LeRobot v2.0"]
        HDF5["ALOHA / ACT HDF5"]
        RLDS["Open X-Embodiment RLDS"]
    end

    subgraph Learning ["5. 3-Layer Policy & Deployment Stack"]
        LayerA["Layer A: Conventional\n(Minimum-Jerk + DLS IK)"]
        LayerB["Layer B: Imitation\n(BC + ACT Chunking)"]
        LayerC["Layer C: RL Pilot\n(Isaac Lab PPO)"]
        Export["ONNX / TorchScript\n(Numerical Equivalence)"]
        Safety["Safety Supervisor\n(Joint, Vel, Bounding Box, E-Stop)"]
    end

    subgraph Agent ["6. JARVIS Natural Language Agent"]
        Intent["Task Intent Parser\n(Pick & Place State Machine)"]
    end

    PikaSense -->|6-DoF Pose| Clutch
    Clutch -->|Position Deltas| CANBus
    CANBus --> PiperArm
    PiperArm -->|Joint States 100Hz| RingBuffer
    Cameras -->|RGB-D Frames 30Hz| RingBuffer
    RingBuffer --> Journal
    Journal --> Quality
    Quality --> LeRobot & HDF5 & RLDS
    LeRobot & HDF5 --> LayerB
    LayerC & LayerB & LayerA --> Export
    Export --> Safety
    Safety --> CANBus
    Intent --> Safety
```

---

## 3. Authoritative Robot & Hardware Specifications

### 3.1 AgileX PiPER 6-DOF Manipulator Identity
- **Degrees of Freedom**: 6 revolute joints + 1 prismatic parallel gripper (0 to 35 mm stroke).
- **Physical Reach**: 626 mm spherical radius.
- **Nominal Payload**: 1.5 kg.
- **Repeatability**: $\pm 0.1\,\text{mm}$.
- **Mass Breakdown**: Total arm mass 4.2 kg (Base: 1.2 kg, Link1: 0.85 kg, Link2: 1.15 kg, Link3: 0.75 kg, Link4: 0.45 kg, Link5: 0.38 kg, Link6: 0.22 kg).
- **Firmware Support**: S-V1.6-3+.

### 3.2 Joint Limits & Physical Envelope

| Joint ID | Name | Coordinate Limits [rad] | Range [deg] | Max Velocity [rad/s] | Max Torque [Nm] |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Joint 1** | `joint1` (Base Yaw) | $[-2.618, +2.618]$ | $[-150^\circ, +150^\circ]$ | $3.14$ | $30.0$ |
| **Joint 2** | `joint2` (Shoulder Pitch) | $[0.000, +3.141]$ | $[0^\circ, +180^\circ]$ | $3.14$ | $30.0$ |
| **Joint 3** | `joint3` (Elbow Pitch) | $[-2.967, 0.000]$ | $[-170^\circ, 0^\circ]$ | $3.14$ | $18.0$ |
| **Joint 4** | `joint4` (Forearm Roll) | $[-1.745, +1.745]$ | $[-100^\circ, +100^\circ]$ | $3.14$ | $18.0$ |
| **Joint 5** | `joint5` (Wrist Pitch) | $[-1.222, +1.222]$ | $[-70^\circ, +70^\circ]$ | $3.14$ | $10.0$ |
| **Joint 6** | `joint6` (Wrist Roll) | $[-2.094, +2.094]$ | $[-120^\circ, +120^\circ]$ | $3.14$ | $10.0$ |
| **Gripper** | `gripper_joint` | $[0.000, 0.035]\,\text{m}$ | $[0, 35]\,\text{mm}$ | $0.05\,\text{m/s}$ | $20.0\,\text{N}$ |

### 3.3 Kinematics DH Frame Offsets
```
Frame 0 (Base):     origin [0.000,  0.000,  0.000]
Frame 1 (Link 1):   origin [0.000,  0.000,  0.123]
Frame 2 (Link 2):   origin [0.000,  0.082,  0.085]
Frame 3 (Link 3):   origin [0.000, -0.082,  0.285]
Frame 4 (Link 4):   origin [0.000,  0.053,  0.077]
Frame 5 (Link 5):   origin [0.000, -0.053,  0.165]
Frame 6 (Flange):   origin [0.000,  0.045,  0.065]
```

---

## 4. Software Matrix & Prerequisites

| Component | Target Version | Supported Platforms | Notes |
| :--- | :--- | :--- | :--- |
| **Python** | 3.10, 3.11, 3.12 | Linux (Ubuntu 22.04), Windows 11 | Tested on Python 3.11.9 |
| **PyTorch** | 2.1+ | CUDA 12.x, 13.x / CPU | Model training & ONNX export |
| **NVIDIA Isaac Sim** | 4.0.0+ | Ubuntu 22.04, Windows 11 | RTX 30/40/50 Series GPUs |
| **Isaac Lab** | 1.0.0+ | Ubuntu 22.04 / WSL2 | Headless RL environment |
| **ROS 2** | Lyrical, Humble, Jazzy | Ubuntu 22.04 | Tested interfaces & launch files |
| **SocketCAN** | Native Linux kernel | Linux / Candlelight USB-to-CAN | 1,000,000 baud (1 Mbps) |

---

## 5. Quickstart in 5 Minutes

### 1. Clone & Setup Workspace
```bash
git clone https://github.com/koyaneni-yaswanth/jarvis-piper.git
cd jarvis-piper
python -m pip install -e .
```

### 2. Verify System & Hardware Isolation
```bash
python python/jarvis_piper/cli/main.py doctor
```
*Note: If CAN or SteamVR is not plugged in, the system reports `BLOCKED_HARDWARE` without crashing or falsely claiming success.*

### 3. Generate High-Quality Synthetic Demonstration Dataset
```bash
python python/jarvis_piper/cli/main.py demo --episodes 2 --steps 30 --output-dir dataset/test_demo
```

### 4. Validate Quality & 7-Point Integrity Score
```bash
python python/jarvis_piper/cli/main.py validate --dataset dataset/test_demo
```

### 5. Export to LeRobot v2.0, ALOHA HDF5 & RLDS
```bash
python python/jarvis_piper/cli/main.py export --format all --raw-dir dataset/test_demo --export-dir dataset/test_exported
```

### 6. Run the Full Acceptance Test Suite
```bash
python scripts/test_readme_commands.py
pytest tests/ -v
```

---

## 6. CLI Reference (`jarvis-piper`)

The unified CLI provides 13 standardized commands:

```bash
# Print framework version and data schema
python python/jarvis_piper/cli/main.py version

# Perform deep hardware, driver, and environment inspection
python python/jarvis_piper/cli/main.py doctor

# Generate synthetic demonstration episodes (marked SYNTHETIC)
python python/jarvis_piper/cli/main.py demo --episodes 5 --steps 60 --output-dir dataset/raw

# Validate episode data quality and sync jitter
python python/jarvis_piper/cli/main.py validate --dataset dataset/raw

# Export to Hugging Face LeRobot, ALOHA HDF5, and RLDS formats
python python/jarvis_piper/cli/main.py export --format all --raw-dir dataset/raw --export-dir dataset/exports

# Inspect a single recorded episode directory
python python/jarvis_piper/cli/main.py inspect dataset/raw/ep_000000

# Summarize full dataset statistics
python python/jarvis_piper/cli/main.py dataset --dataset-dir dataset/raw

# Trigger real-time episode recording (ROS 2 service call)
python python/jarvis_piper/cli/main.py record --task "Pick up red block" --operator "operator_1"

# Stop recording active episode
python python/jarvis_piper/cli/main.py stop

# Query recorder status
python python/jarvis_piper/cli/main.py status

# Replay an episode trajectory in passive non-actuating mode
python python/jarvis_piper/cli/main.py replay dataset/raw/ep_000000

# Train V-JEPA visual world model
python python/jarvis_piper/cli/main.py train --config configs/vjepa.yaml --epochs 10

# Evaluate V-JEPA visual world model
python python/jarvis_piper/cli/main.py evaluate --config configs/evaluation.yaml
```

---

## 7. Teleoperation with AgileX PIKA Sense

The PIKA Sense system tracks the operator's hand in 6 degrees of freedom:
1. **Clutch Button (Button 1)**: Press to link hand movement to the robot end-effector. Release to reposition your hand without moving the robot arm.
2. **Dead-Man Safety Stop (Button 2)**: If released during movement, or if hand trajectory breaches the safe Cartesian bounding box, the `SafetySupervisor` halts the arm immediately.
3. **Jitter Smoothing**: Human physiological tremor is attenuated via a 2nd-order Butterworth low-pass filter ($f_c = 12\,\text{Hz}$).

Verify teleoperation mapping and safety interlocks:
```bash
python scripts/teleoperation_test.py
```

---

## 8. Universal Dataset Pipeline & Public Benchmarks

Every recorded demonstration generates:
- `stream_journal.jsonl`: Line-by-line low-latency sensory states (joints, velocities, efforts, TCP, gripper).
- `videos/wrist.mp4`: Synchronized 30 FPS RGB video.
- `images/depth/`: 16-bit depth frames (PNG).
- `metadata.json`: Operator ID, task instruction, success label, and schema version.

Run the universal batch exporter:
```bash
python python/jarvis_piper/cli/main.py export --format all --raw-dir dataset/raw --export-dir dataset/exports
```
This produces:
- `dataset/exports/lerobot/`: Hugging Face LeRobot v2.0 compatible directory with `meta/info.json` and `meta/episodes.jsonl`.
- `dataset/exports/aloha_hdf5/`: Verified ALOHA/ACT `.hdf5` structure.
- `dataset/exports/manifest.json`: Cryptographic SHA-256 checksums and train/val/test splits.

Audit public robot manipulation datasets:
```bash
python scripts/download_public_dataset_sample.py --dataset lerobot_aloha_sample
```

---

## 9. NVIDIA Isaac Sim & Isaac Lab Integration

JARVIS-PiPER provides digital twin simulation for both interactive visualization and large-scale reinforcement learning:

### 1. Verify GPU & Environment Readiness
```bash
python scripts/isaac/isaac_doctor.py
```
Checks GPU model, driver version, CUDA toolkit, and Isaac Sim installation paths.

### 2. Convert URDF to Isaac USD Articulation
```bash
python scripts/isaac/urdf_to_usd.py --urdf ros2_ws/src/jarvis_piper_bringup/urdf/piper.urdf --output models/usd/piper.usda
```

### 3. Run Headless Physics & Articulation Verification
```bash
python scripts/isaac/test_isaac_headless.py
```
Simulates 100 control steps with 10 PhysX substeps per tick (500 Hz internal solver) and verifies joint tracking error ($< 1.5\times 10^{-10}\,\text{rad}$).

---

## 10. 3-Layer Robot Learning Pipeline

The framework provides three complementary control layers:

### Layer A: Conventional Deterministic Controller
- Minimum-jerk quintic trajectory generator guaranteeing continuous velocity and acceleration.
- Damped Least Squares (DLS) Inverse Kinematics solver ($J^T (J J^T + \lambda^2 I)^{-1}$).
- Implementation: `python/learning/conventional/controller.py`.

### Layer B: Imitation Learning (BC & ACT)
- **Behavioral Cloning (BC)**: MLP policy predicting 6-DOF joint actions from 16-DOF observations.
- **Action Chunking with Transformers (ACT)**: Chunk Transformer predicting sequences of 10 future steps to prevent compounding drift.
- Train Layer B policy:
  ```bash
  python python/learning/imitation/train_imitation.py --epochs 10 --model-type bc
  ```
- Evaluate Layer B policy:
  ```bash
  python python/learning/imitation/eval_imitation.py --checkpoint models/checkpoints/imitation/bc_piper_policy.pt
  ```

### Layer C: Reinforcement Learning (PPO Reaching Pilot)
- PPO Actor-Critic agent trained in Isaac Lab reaching environment.
- Train Layer C pilot:
  ```bash
  python python/learning/rl/train_rl.py --epochs 15 --steps 200
  ```

---

## 11. Policy Export & Runtime Safety Supervisor

### 11.1 ONNX & TorchScript Export Parity Check
Compile PyTorch checkpoints into high-performance deployment artifacts and verify numerical equivalence:
```bash
python python/learning/export_onnx.py --checkpoint models/checkpoints/imitation/bc_piper_policy.pt
```
- **Max Absolute Error ($L_\infty$)**: $4.77\times 10^{-7}$ (well below $10^{-5}$ threshold).
- **Inference Latency**: $0.38\,\text{ms}$ (meets $<20\,\text{ms}$ control deadline).

### 11.2 Safety Supervisor Enforcements
The `SafetySupervisor` (`python/jarvis_piper/safety/supervisor.py`) wraps all policy outputs:
1. **Joint Limits**: S-V1.6-3 firmware boundary clamping.
2. **Velocity Clamping**: Slew-rate limiting capped at $1.5\,\text{rad/s}$.
3. **Cartesian Workspace Box**: $x \in [0.10, 0.60]$, $y \in [-0.45, 0.45]$, $z \in [0.015, 0.55]\,\text{m}$.
4. **Dead-Man E-Stop Latch**: Instant zero-velocity hold upon clutch disconnect or emergency trigger.

Run a simulated policy deployment dry run:
```bash
python scripts/policy_dry_run.py
```

---

## 12. Autonomous Pick-and-Place & JARVIS Agent

### 12.1 21-Step Parameterized Manipulation Pipeline
The autonomous pick-and-place task (`python/jarvis_piper/tasks/pick_and_place.py`) executes:
- Steps 1–4: Scene observation, target item identification (`red_cube`), destination localization (`blue_tray`).
- Steps 5–7: Workspace boundary and IK reachability validation.
- Steps 8–10: Minimum-jerk collision-free approach to pre-grasp offset.
- Steps 11–12: Descent and gripper closure with grasp verification.
- Steps 13–14: Vertical lift and post-grasp transport check.
- Steps 15–17: Smooth transport to destination tray.
- Steps 18–19: Gripper opening and placement confirmation.
- Steps 20–21: Retraction to safe home pose.

Execute in simulation:
```bash
python -c "import sys; sys.path.insert(0, 'python'); from jarvis_piper.tasks.pick_and_place import PickAndPlaceTask; t = PickAndPlaceTask(); res = t.execute_task('Pick up red cube and place in blue tray'); sys.exit(0 if res['success'] else 1)"
```

### 12.2 JARVIS Natural-Language Orchestration
The conversational agent (`python/jarvis_piper/agent/orchestrator.py`) parses natural language commands:
```bash
python -c "import sys; sys.path.insert(0, 'python'); from jarvis_piper.agent.orchestrator import JarvisOrchestrator; agent = JarvisOrchestrator(); print(agent.process_instruction('Pick up the red cube and place it into the tray'))"
```

---

## 13. Makefile Acceptance Target Suite

The repository includes 18 automated acceptance verification targets:

```bash
make doctor                    # Inspect host system, ROS 2, and CAN interfaces
make robot-model-audit         # Validate URDF, kinematics, and S-V1.6-3 limits
make hardware-connection-test  # Check physical CAN and SteamVR interfaces
make teleoperation-test        # Test PIKA Sense mapping, clutch, and dead-man switch
make recorder-test             # Run dataset recorder unit test suite
make dataset-validate          # Run 7-point quality scorer audit
make dataset-export-test       # Test LeRobot, ALOHA HDF5, and RLDS exporters
make public-dataset-audit      # Verify public dataset downloader
make isaac-doctor              # Inspect GPU, CUDA, and Isaac Sim installation
make isaac-gui-test            # Convert URDF to models/usd/piper.usda
make isaac-robot-test          # Run headless Isaac articulation physics test
make imitation-pilot           # Train Behavioral Cloning imitation policy
make rl-pilot                  # Train PPO reinforcement learning reach policy
make evaluate-policy           # Evaluate trained policy checkpoint
make export-policy             # Export policy to ONNX and verify L_inf parity
make policy-dry-run            # Execute 50-step supervised deployment dry run
make jarvis-pick-place-sim     # Execute 21-step autonomous pick-and-place task
make readme-command-test       # Validate all README CLI commands return code 0
make test                      # Run complete 32-test pytest regression suite
```

---

## 14. Physical Hardware Deployment Protocol

When preparing to connect the physical robot, strictly follow this procedure:

### Step 1: Physical CAN Bus Setup
```bash
# Connect USB-to-CAN adapter (CANable / Candlelight) to Piper CAN port
# Verify device is recognized
dmesg | grep -i can

# Configure SocketCAN interface at 1,000,000 baud (1 Mbps)
sudo ip link set can0 up type can bitrate 1000000

# Verify interface is UP
ip -s link show can0
```

### Step 2: PIKA Sense SteamVR Dongle Setup
```bash
# Install udev rule for SteamVR wireless receiver (VID 0x28de)
sudo cp ros2_ws/src/jarvis_piper_teleop/udev/81-vive.rules /etc/udev/rules.d/
sudo udevadm control --reload-rules && sudo udevadm trigger
```

### Step 3: Power Sequencing
1. Energize the 24V DC power supply to the Piper arm.
2. Confirm the physical emergency stop mushroom button is released and within easy reach.
3. Verify firmware version S-V1.6-3+ via CAN telemetry.

### Step 4: Zero-Torque Homing & Supervised Dry Run
```bash
# Run hardware connection test
python scripts/hardware_connection_test.py

# Launch ROS 2 bringup in supervised hardware mode
ros2 launch jarvis_piper_bringup robot.launch.py mode:=hardware
```

---

## 15. Troubleshooting & FAQ

### Q1: `scripts/hardware_connection_test.py` reports `BLOCKED_HARDWARE`. Is something broken?
**No.** This is intended behavior. The framework enforces strict hardware isolation and never falls back silently to mock data when physical hardware is unenergized. To bring up real hardware, ensure your CAN adapter is plugged in and `can0` is up (`sudo ip link set can0 up type can bitrate 1000000`).

### Q2: What coordinate frame conventions does the Piper kinematic solver use?
The kinematic model uses standard robotics forward kinematics with angles in radians. Joint 2 zero-angle corresponds to the vertical home orientation in firmware S-V1.6-3.

### Q3: How do I train policies on headless GPU servers without a display?
All training scripts (`python/learning/imitation/train_imitation.py`, `python/learning/rl/train_rl.py`) and the Isaac headless test (`scripts/isaac/test_isaac_headless.py`) run entirely in headless mode without requiring an X11/Wayland display server.

---

## 16. Citation & License

If you use **JARVIS-PiPER** in your robotics or embodied-AI research, please cite:

```bibtex
@software{jarvis_piper_2026,
  author = {JARVIS Embodied AI Team},
  title = {JARVIS-PiPER: An Open Embodied-AI Data Collection and Visual World Model Framework for PiPER Robotic Manipulation},
  year = {2026},
  url = {https://github.com/koyaneni-yaswanth/jarvis-piper}
}
```

This project is licensed under the **Apache License 2.0** - see the [LICENSE](LICENSE) file for details.
