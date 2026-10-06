# JARVIS-PiPER

<div align="center">

# JARVIS-PiPER: An Open Embodied-AI Data Collection and Visual World Model Framework for PiPER Robotic Manipulation

[![ROS 2 Lyrical](https://img.shields.io/badge/ROS_2-Lyrical-blue.svg)](https://docs.ros.org/en/rolling/Releases/Release-Lyrical-Llama.html)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-green.svg)](LICENSE)
[![CI Build](https://img.shields.io/badge/CI-Passing-brightgreen.svg)](.github/workflows/ci.yml)
[![V-JEPA Ready](https://img.shields.io/badge/World_Model-V--JEPA-orange.svg)](docs/vjepa.md)

</div>

---

## 🚀 Overview

**JARVIS-PiPER** is an open-source, production-grade embodied-AI data collection platform, multi-modal dataset pipeline, and visual world-model learning framework designed around the **AgileX PIKA Sense + PIKA Station + PiPER 6-DOF Robotic Arm** system.

It bridges teleoperation, sensory synchronization, crash-resilient raw recording, 7-point dataset quality assurance, universal dataset formatting (**LeRobot 2.0, ALOHA HDF5, RLDS/Open X-Embodiment, ROS 2 MCAP**), and self-supervised **V-JEPA visual world modeling**.

### 🌟 Key Highlights

- **4 Decoupled Operating Modes**:
  - `HARDWARE`: Real AgileX PIKA Sense handheld 6-DoF teleoperator, PiPER arm, and parallel gripper over CAN & ROS 2.
  - `SIMULATION`: Full physics & contact simulation in Gazebo Harmonic.
  - `MOCK`: High-fidelity synthetic multi-modal telemetry generator (runs anywhere with zero hardware).
  - `REPLAY`: Passive, safe dataset player for offline playback and model validation.
- **Hardware Abstraction Layer (HAL)**: Pluggable `RobotInterface`, `CameraInterface`, `GripperInterface`, and `TeleoperationInterface` isolating machine-specific hardware from learning pipelines.
- **Zero Frame-Drop Multi-Modal Sync**: Lock-free circular ring buffer aligning joint states (50-100Hz), teleoperation poses (50Hz), RGB cameras (30Hz), 16-bit depth maps (30Hz), and live TF trees within an adaptive slop window ($< 25\text{ms}$).
- **Universal Embodied AI Dataset Generator**: Single-command batch exporter to Hugging Face **LeRobot v2.0**, **ALOHA / ACT HDF5**, **RLDS / Open X-Embodiment**, and **JARVIS World-Model Transitions**.
- **V-JEPA Visual World Model**: Modular self-supervised visual predictive model with temporal masked context encoders, EMA target encoders, and latent rollout predictors.

---

## 📦 Architecture

```
                    HUMAN OPERATOR (Language Instruction)
                                      │
                                      ▼
                        ┌───────────────────────────┐
                        │        PIKA SENSE         │  6-DoF spatial tracker
                        │   (Teleoperation Hub)     │  Buttons, clutch & grips
                        └─────────────┬─────────────┘
                                      │
                             /pika_pose, /gripper/ctrl
                                      ▼
                        ┌───────────────────────────┐
                        │      PiPER 6-DOF ARM      │  Revolute joints q1..q6
                        │    & Parallel Gripper     │  0-35mm stroke claw
                        └─────────────┬─────────────┘
                                      │
============================ ROS 2 LYRICAL BUS ============================
   /joint_states        /camera/color/image_raw       /tf, /tf_static
   /gripper/data        /camera/depth/image_rect      /imu/data
======================================┬====================================
                                      ▼
                       ┌─────────────────────────────┐
                       │      TIME SYNCHRONIZER      │
                       │   - Adaptive Slop Window    │
                       │   - Lock-free Ring Buffer   │
                       └──────────────┬──────────────┘
                                      ▼
                       ┌─────────────────────────────┐
                       │      EPISODE RECORDER       │
                       │   - Streaming Raw Journal   │
                       │   - Async Image/Video Pool  │
                       └──────────────┬──────────────┘
                                      ▼
                       ┌─────────────────────────────┐
                       │     QUALITY ASSURANCE (QA)  │
                       │   - 7-Point Integrity Check │
                       │   - Tiers A, B, C, D Scoring│
                       └──────────────┬──────────────┘
                                      ▼
                       ┌─────────────────────────────┐
                       │  DATASET & WORLD MODEL      │
                       │  ├─ LeRobot v2.0            │
                       │  ├─ ALOHA / ACT HDF5        │
                       │  ├─ RLDS / Open X-Embodiment│
                       │  └─ V-JEPA World Model      │
                       └─────────────────────────────┘
```

---

## 🛠️ Quick Start

### 1. Clone & Setup
```bash
git clone https://github.com/koyaneni-yaswanth/jarvis-piper.git
cd jarvis-piper
./scripts/install.sh
./scripts/setup.sh
```

### 2. Verify System Health
```bash
jarvis-piper doctor
```

### 3. Generate Mock Demo Episode (Zero Hardware Needed)
```bash
jarvis-piper demo --episodes 2 --steps 90
```

### 4. Validate Dataset Quality
```bash
jarvis-piper validate --dataset dataset/raw/
```

### 5. Export to All Machine Learning Formats
```bash
jarvis-piper export --format all
```

### 6. Train V-JEPA World Model
```bash
jarvis-piper train --config configs/vjepa.yaml
```

---

## 💻 CLI Commands

| Command | Description |
|---|---|
| `jarvis-piper doctor` | Runs comprehensive system, hardware, and ROS 2 diagnostics |
| `jarvis-piper demo` | Generates synthetic multi-modal demonstration episodes |
| `jarvis-piper record` | Starts interactive episode recording with language instruction |
| `jarvis-piper stop` | Safely stops active recording and triggers quality audit |
| `jarvis-piper status` | Queries live recorder state, frame counts, and buffer usage |
| `jarvis-piper validate` | Executes 7-point QA audit across episodes |
| `jarvis-piper inspect` | CLI visualizer for trajectories, joint curves, and telemetry |
| `jarvis-piper replay` | Replays recorded episode without physical actuation |
| `jarvis-piper dataset` | Summarizes dataset statistics and joint coverage |
| `jarvis-piper export` | Batch exports to LeRobot, ALOHA HDF5, RLDS, and World Model |
| `jarvis-piper train` | Trains V-JEPA visual world model on recorded dataset |
| `jarvis-piper evaluate` | Evaluates representation quality and multi-step rollouts |
| `jarvis-piper version` | Prints software versions and schema specifications |

---

## 📄 License & Citation

Licensed under the [Apache 2.0 License](LICENSE).

```bibtex
@software{jarvis_piper_2026,
  author = {JARVIS Embodied AI Team},
  title = {JARVIS-PiPER: An Open Embodied-AI Data Collection and Visual World Model Framework for PiPER Robotic Manipulation},
  year = {2026},
  url = {https://github.com/your-org/jarvis-piper}
}
```
