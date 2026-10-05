# JARVIS-PiPER System Architecture

## 1. High-Level Architectural Overview

**JARVIS-PiPER** is an open-source, production-grade Embodied-AI Data Collection and Visual World Model platform engineered for the **AgileX PIKA Sense + PIKA Gripper + PiPER 6-DOF robotic arm** ecosystem. It bridges low-level teleoperation and high-frequency real-time robotics telemetry with frontier foundation model representation learning (specifically V-JEPA - Video Joint-Embedding Predictive Architecture).

The platform is designed around strict decoupling principles to ensure it functions across development workstations, remote CI runners, simulation environments, and physical laboratory setups without code modification.

```
                              JARVIS-PiPER CLI
                                      │
              ┌───────────────────────┼───────────────────────┐
              ▼                       ▼                       ▼
        HARDWARE MODE          SIMULATION MODE            MOCK MODE
    (PIKA Sense + PiPER)     (Gazebo Harmonic Sim)    (Synthetic Streamer)
              │                       │                       │
              └───────────────────────┼───────────────────────┘
                                      ▼
                        HARDWARE ABSTRACTION LAYER (HAL)
                        - RobotInterface / PiperHardwareAdapter
                        - GripperInterface / PikaGripperAdapter
                        - TeleoperationInterface / PikaSenseAdapter
                        - CameraInterface / OpenCV-DepthAI
                                      │
                                      ▼
                             ROS 2 LYRICAL BUS
                                      │
                        TIME SYNCHRONIZER & RECORDER
                                      │
                                      ▼
                              RAW DATA JOURNAL
                                      │
                                      ▼
                        VALIDATION & QUALITY SCORER
                               (Tiers A, B, C, D)
                                      │
                                      ▼
                         UNIVERSAL DATASET GENERATION
                     (LeRobot, ALOHA HDF5, RLDS, MCAP)
                                      │
                                      ▼
                         V-JEPA VISUAL WORLD MODEL
                         - Multi-frame Temporal Clips
                         - Context / Target Masked Encoders
                         - Latent Predictor & Loss Engine
```

---

## 2. Core Subsystems

### 2.1 Hardware Abstraction Layer (HAL)
Located in `python/jarvis_piper/hardware/`, the HAL isolates robot drivers and transport protocols behind abstract interfaces:
- `RobotInterface`: Exposes `get_joint_states()`, `get_tcp_pose()`, `command_joint_position()`, and safety limits.
- `GripperInterface`: Standardizes gripper opening stroke ($0.0 \text{ m}$ to $0.035 \text{ m}$) and grip effort.
- `TeleoperationInterface`: Ingests optical 6-DOF poses from PIKA Sense and converts them to arm target commands.
- `CameraInterface`: Manages RGB and depth streaming from wrist-mounted and stationary cameras.

Adapters include `PiperHardwareAdapter`, `PikaSenseAdapter`, `PikaGripperAdapter`, and `MockPiperAdapter`.

### 2.2 Time Synchronizer & Ring Buffer
Located in `ros2_ws/src/jarvis_piper_sync/`:
- Solves multi-frequency alignment between high-rate arm telemetry ($50\text{--}100\text{ Hz}$) and camera vision frames ($30\text{ Hz}$).
- Maintains a thread-safe sliding ring buffer for each channel.
- Uses an adaptive slop window ($\pm 15\text{--}30\text{ ms}$) to pair nearest frames without pipeline stalls.
- Publishes atomic `SynchronizedFrame.msg` containing joint states, gripper stroke, Cartesian pose, and aligned camera frame identifiers.

### 2.3 Non-Blocking Crash-Proof Recorder
Located in `ros2_ws/src/jarvis_piper_recorder/`:
- Asynchronously logs incoming synchronized frames using dedicated I/O worker threads.
- Maintains an append-only transaction journal (`stream_journal.jsonl`) flushed to disk after every frame. If power is interrupted or the process terminated, zero recorded frames are corrupted.
- Automatically compiles episode summaries into `trajectory.json` and `metadata.json` upon graceful completion.

### 2.4 Quality Scorer & Validation Auditor
Located in `python/dataset/quality.py`:
- Audits episodes for timestamp monotonicity, dropped frame ratios, joint velocity spikes, and trajectory jerk.
- Classifies datasets into Tiers:
  - **Tier A**: $\le 0.1\%$ frame drops, zero NaN/Inf values, smooth jerk profile. Recommended for foundation model training.
  - **Tier B**: $\le 1.0\%$ frame drops, valid metadata. Acceptable for imitation learning.
  - **Tier C / D**: Anomalies detected; flagged for review.

### 2.5 Universal Dataset Exporters
Located in `python/dataset/exporters.py` and `ros2_ws/src/jarvis_piper_dataset/`:
- **LeRobot v2.0**: Compatible with Hugging Face LeRobot dataset conventions.
- **ALOHA / ACT HDF5 / NPZ**: Compatible with Tony Z. Zhao's Action Chunking with Transformers (ACT).
- **RLDS / Open X-Embodiment**: Standard format for large-scale robot learning and VLA models (e.g. RT-1, RT-2, Octo).

### 2.6 V-JEPA Visual World Model
Located in `python/world_model/vjepa/`:
- Self-supervised multi-frame visual representation model.
- Predicts missing spatio-temporal video blocks in latent embedding space rather than reconstructing raw RGB pixels.
- Provides context representations for downstream policy learning and trajectory rollout evaluation.
