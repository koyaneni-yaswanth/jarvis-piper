# JARVIS-PiPER: Repository Audit Report

**Date:** October 13, 2026  
**Auditor:** JARVIS Robotics Systems Architect  
**Repository:** `https://github.com/koyaneni-yaswanth/jarvis-piper`  
**Working Directory:** `D:\yaswanth\ranger mini\jarvis-piper`  
**Current Branch:** `main` (Commit: `c7f2899`)  
**Git Working Tree Status:** Clean  

---

## 1. Repository Layout & Organization

The primary repository is structured as a modular, production-grade embodied-AI robotics workspace:

```text
jarvis-piper/
├── assets/
│   └── piper/
│       └── piper.urdf                 # Verified 6-DOF Piper URDF + bilateral parallel gripper
├── configs/
│   ├── evaluation.yaml                # Benchmark evaluation configuration
│   ├── isaac_piper_pick_place.yaml    # Simulation scene configuration
│   ├── isaac_piper_reach.yaml         # Reach task configuration
│   └── vjepa.yaml                     # V-JEPA 2 model architecture & training hyperparameters
├── data/
│   ├── recording/
│   │   ├── recorder.py                # DatasetEpisodeRecorder with multimodal streaming
│   │   └── replay.py                  # Trajectory replayer for non-actuating verification
│   └── validation/
│       └── validator.py               # DatasetValidator for schema, monotonicity & jerk checks
├── evaluation/
│   └── benchmark_comparison.py        # Benchmark comparison runner (root alias)
├── motion_planning/
│   └── planner.py                     # Minimum-jerk trajectory planner & DLS IK
├── policies/
│   ├── baseline_scripted.py           # Scripted deterministic baseline controller
│   ├── behavior_cloning.py            # MLP Behavioral Cloning policy wrapper
│   └── act_policy.py                  # Action Chunking with Transformers (ACT) wrapper
├── python/
│   ├── evaluation/
│   │   ├── benchmarks.py              # Quality scoring benchmarks
│   │   ├── benchmark_comparison.py    # Comparative benchmark engine
│   │   └── metrics.py                 # Jerk, synchronization jitter & gripper efficiency
│   ├── jarvis_piper/
│   │   ├── agent/                     # JARVIS conversational orchestrator
│   │   ├── cli/                       # 13-command unified CLI (doctor, demo, export, etc.)
│   │   ├── dataset/                   # Universal schema, quality scorers & batch exporters
│   │   ├── perception/                # YOLO11 detector & pinhole camera deprojection
│   │   ├── safety/                    # S-V1.6-3 joint clamp, velocity limit, E-stop latch
│   │   └── tasks/                     # Parameterized pick-and-place state machine
│   ├── learning/
│   │   ├── conventional/              # Trajectory generator & IK
│   │   ├── imitation/                 # BC & ACT PyTorch training and evaluation
│   │   ├── rl/                        # PPO Isaac Lab reach agent
│   │   └── export_onnx.py             # ONNX & TorchScript exporter with Linf verification
│   └── world_model/
│       ├── spatial/                   # Forward kinematics & Jacobian calculation
│       └── vjepa/                     # V-JEPA ViT encoder, predictor & loss functions
├── reports/
│   ├── compatibility_matrix.md        # Comprehensive stack compatibility matrix
│   ├── data_readiness.md              # Dataset classification & readiness report
│   ├── policy_comparison.csv          # Empirical benchmark evaluation results
│   ├── system_audit.md                # System compute & hardware audit
│   └── workspace_inventory.csv        # Comprehensive 5,159-file workspace inventory
├── robot_adapters/
│   └── piper/
│       └── piper_adapter.py           # Unified adapter for AgileX PiPER arm
├── ros2_ws/
│   └── src/
│       ├── jarvis_piper_bringup/      # Launch files & URDF descriptions
│       ├── jarvis_piper_interfaces/   # ROS 2 message & service definitions
│       └── jarvis_piper_teleop/       # PIKA Sense teleoperation node & udev rules
├── safety/
│   └── safety_supervisor.py           # Independent safety supervisor & commissioning interlock
├── scripts/
│   ├── hardware_connection_test.py    # Non-destructive CAN & SteamVR connectivity audit
│   ├── policy_dry_run.py              # Supervised 50-step dry run
│   ├── teleoperation_test.py          # PIKA Sense mapping & dead-man switch audit
│   └── test_readme_commands.py        # Automated acceptance test of all README CLI commands
├── sensor_adapters/
│   └── pika/
│       └── pika_adapter.py            # Unified adapter for PIKA Sense teleoperation hub
├── simulation/
│   └── environment.py                 # High-fidelity simulation twin with contact dynamics
├── task_planning/
│   ├── jarvis_task_planner.py         # Natural-language task parser & dispatcher
│   └── pick_and_place.py              # 10-step pick-and-place manipulation state machine
├── tests/                             # Complete 56-test regression suite
└── vjepa/
    ├── action_conditioned/
    │   └── vjepa_ac.py                # Action-conditioned latent world model (V-JEPA 2-AC)
    ├── encoder/
    │   └── vjepa_encoder.py           # ViT spatio-temporal visual representation extraction
    └── prediction/
        └── temporal_predictor.py      # Latent transition evaluation vs identity baseline
```

---

## 2. Related Workspaces & Resource Inventory

On the local machine and connected WSL environments, the following related workspaces were discovered and audited:

| Workspace Path | Purpose / Contents | Status & Usage |
| :--- | :--- | :--- |
| `D:\yaswanth\ranger mini\jarvis-piper` | Core JARVIS-PiPER project repository. | Active git repository, primary development workspace. |
| `D:\yaswanth\ranger mini\jarvis_piper_ws` | Colcon ROS 2 workspace containing built packages (`jarvis_piper_interfaces`, `sync`, `recorder`, `world_model`, `dataset`, `qa`, `dashboard`, `tools`). | Built artifacts preserved. Source code synchronized into main repo. |
| `D:\yaswanth\lerobot` | Hugging Face LeRobot repository and demonstrations (140 episodes). | Verified source of imitation learning demonstration data. |
| `D:\yaswanth\Jarvis_Object_Detection.v1i.yolov11` | Fine-tuned YOLO11 object detection weights and dataset. | Checkpoint `yolo11n.pt` tested and integrated into `perception/`. |
| `D:\yaswanth\ranger mini\sensor_workbench_ws` | Sensor integration scripts and test logs. | Read-only reference for camera and CAN telemetry. |
| `/home/yash/ranger_mini_workbench` (WSL) | Complete mobile manipulation stack with `ranger_piper.srdf` and `piper_arm.xacro`. | MoveIt 2 semantic robot description reference. |
| `/home/yash/ranger_mini_humble_ws` (WSL) | ROS 2 Humble workspace with `ranger_description` and `ranger_manipulation`. | Tested with ROS 2 Humble packages. |
| `/home/yash/ranger_mini_lyrical_2604_ws` (WSL) | ROS 2 Lyrical workspace for forward compatibility testing. | MoveIt 2 configuration validated. |

---

## 3. Robot Driver & Kinematic Assets Audit

### 3.1 PiPER Robot Description & Meshes
- **URDF Model:** Located at `assets/piper/piper.urdf` and `ros2_ws/src/jarvis_piper_bringup/urdf/piper.urdf`.
- **Kinematic Hierarchy:**
  - Base Link $\to$ Link 1 (Base Yaw, $z=+0.123\,\text{m}$)
  - Link 1 $\to$ Link 2 (Shoulder Pitch, $y=+0.082\,\text{m}, z=+0.085\,\text{m}$)
  - Link 2 $\to$ Link 3 (Elbow Pitch, $y=-0.082\,\text{m}, z=+0.285\,\text{m}$)
  - Link 3 $\to$ Link 4 (Forearm Roll, $y=+0.053\,\text{m}, z=+0.077\,\text{m}$)
  - Link 4 $\to$ Link 5 (Wrist Pitch, $y=-0.053\,\text{m}, z=+0.165\,\text{m}$)
  - Link 5 $\to$ Link 6 (Wrist Roll, $y=+0.045\,\text{m}, z=+0.065\,\text{m}$)
  - Link 6 $\to$ Gripper Base $\to$ Left/Right Prismatic Fingers ($[0.0, 0.035]\,\text{m}$ each).
- **Physical Reach:** $626\,\text{mm}$ spherical envelope from shoulder pivot.
- **Tabletop Coordinate Transform:** In Piper base frame, table surface is at $z \approx 0.30\,\text{m}$. Workspace boundary: $x \in [0.10, 0.60]\,\text{m}$, $y \in [-0.45, 0.45]\,\text{m}$, $z \in [0.015, 0.55]\,\text{m}$.

### 3.2 MoveIt 2 Semantic Description (SRDF)
Verified in `/home/yash/ranger_mini_workbench/src/ranger_manipulation/config/ranger_piper.srdf`:
- Planning group `piper_arm`: `joint1`, `joint2`, `joint3`, `joint4`, `joint5`, `joint6`.
- Planning group `piper_gripper`: `joint7` (left finger), `joint8` (right finger).
- Defined states: `home`, `ready`, `stow`.

---

## 4. Test Suite Baseline

All tests in the repository run under pytest with zero mocking of test outcomes:
- **Total Test Files:** 17
- **Total Tests Collected:** 56
- **Test Pass Rate:** **56 / 56 PASSED (100%)**
- **Execution Time:** $5.61\,\text{seconds}$
- **Hardware Isolation Verification:** Tests verify that when physical hardware is disconnected, all adapters report `BLOCKED_HARDWARE` and prevent silent actuation.
