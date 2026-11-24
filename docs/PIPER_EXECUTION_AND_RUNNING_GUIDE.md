# AgileX PiPER Robot Arm — Comprehensive Projects & Execution Manual

> **Workstation Target:** Ubuntu 22.04 LTS (x86_64 / Intel Core Ultra 5) | ROS 2 Humble  
> **Hardware:** AgileX PiPER 6-DOF Robotic Arm | CAN interface `can0` @ 1,000,000 bps (1 Mbps)  
> **Sensors & Teleoperators:** AgileX PIKA Sense (SteamVR Lighthouse v2.0), Synexens CS20 ToF, Intel RealSense (D405 / D435), Meta Quest VR

This manual serves as the central operational guide and running reference for all AgileX PiPER manipulation, digital twin simulation, bare-hand gesture teleoperation, singularity avoidance, and bimanual robotics projects developed on this workstation.

---

## Table of Contents
1. [Global System Shortcuts & CAN Configuration](#1-global-system-shortcuts--can-configuration)
2. [PiPER ROS 2 Manipulation Workstation (`PiPER_ROS2_Manipulation`)](#2-piper-ros-2-manipulation-workstation-piper_ros2_manipulation)
3. [PiPER Genesis Digital Twin & Multi-Modal Control (`piper_genesis_project`)](#3-piper-genesis-digital-twin--multi-modal-control-piper_genesis_project)
4. [Bare-Hand Gesture Teleoperation Stack (`piper_gesture_ws`)](#4-bare-hand-gesture-teleoperation-stack-piper_gesture_ws)
5. [Singularity Avoidance & Safety Gate GUI (`PiPER_Physical_Control`)](#5-singularity-avoidance--safety-gate-gui-piper_physical_control)
6. [ROS 2 Kinematics & Null-Space Cartesian Control (`ros2_workspace`)](#6-ros-2-kinematics--null-space-cartesian-control-ros2_workspace)
7. [Official AgileX PiPER Core Stack (`piper_ros`)](#7-official-agilex-piper-core-stack-piper_ros)
8. [JARVIS-PiPER Embodied AI & PIKA Sense Teleop (`jarvis-piper`)](#8-jarvis-piper-embodied-ai--pika-sense-teleop-jarvis-piper)
9. [Bimanual PiPER Dual-Arm Manipulation Platform (`bimanual_piper`)](#9-bimanual-piper-dual-arm-manipulation-platform-bimanual_piper)
10. [Meta Quest VR Teleoperation (`QuestArmTeleop`)](#10-meta-quest-vr-teleoperation-questarmteleop)
11. [Standalone Direct Scripts & Verification Utilities](#11-standalone-direct-scripts--verification-utilities)

---

## 1. Global System Shortcuts & CAN Configuration

Ensure the SocketCAN interface is brought up at 1 Mbps before physical execution:
```bash
sudo ip link set can0 type can bitrate 1000000
sudo ip link set can0 up
```

Convenience terminal utilities configured in `~/.local/bin/`:
* **`piper_launch`**: Launches the complete MoveIt 2 manipulation workstation, C++ `ros2_control` hardware interface, RViz 2 slider panel, and autonomous pick-and-place action server.
* **`piper_recover`**: Instantly clears CAN `0x150` emergency stop / fault state, cycles controller setpoints, re-energizes holding torque, and restores `HARDWARE_EXECUTING` state (< 1.2s).
* **`piper_home`**: Executes fast recovery and smoothly drives the physical arm to the safe home pose via MoveIt 2.

---

## 2. PiPER ROS 2 Manipulation Workstation (`PiPER_ROS2_Manipulation`)
* **Path:** `/home/humble/PiPER_ROS2_Manipulation`
* **Key Features:**
  - Native C++ `PiperHardwareInterface` (`ros2_control` SystemInterface plugin) on `can0` at 100 Hz.
  - MoveIt 2 motion planning (OMPL RRTConnect, Pilz Cartesian, CHOMP).
  - Embedded native RViz 2 panel with 7-DOF interactive sliders, E-stop, and 1-Click Fast Recovery.
  - 11-stage autonomous industrial pick-and-place action server (`/piper/pick_place`).
  - Real-time kinematic singularity monitor (25 Hz).

### Execution Commands:
```bash
# Complete system launch (hardware + MoveIt 2 + RViz 2 panel):
piper_launch

# Or via script:
cd /home/humble/PiPER_ROS2_Manipulation && ./run_all.sh

# Or standard ROS 2 command:
source /opt/ros/humble/setup.bash
source /home/humble/piper_ros/install/setup.bash
source /home/humble/PiPER_ROS2_Manipulation/install/setup.bash
ros2 launch piper_manipulation_bringup hardware.launch.py
```

### Alternative Operating Modes:
```bash
# Pure Mock Simulation (no CAN hardware needed):
ros2 launch piper_manipulation_bringup simulation.launch.py

# Passive Read-Only Diagnostic Mode (receives joint telemetry, motors unpowered):
ros2 launch piper_manipulation_bringup hardware_read_only.launch.py
```

### Autonomous Pick & Place Commands:
```bash
# Dry-run validation (Plan only):
ros2 action send_goal /piper/pick_place piper_pick_place/action/PickPlace "{object_id: 'target_cube', plan_only: true}"

# Physical execution:
ros2 action send_goal /piper/pick_place piper_pick_place/action/PickPlace "{object_id: 'target_cube', plan_only: false}"
```

---

## 3. PiPER Genesis Digital Twin & Multi-Modal Control (`piper_genesis_project`)
* **Path:** `/home/humble/piper_genesis_project`
* **Key Features:**
  - Genesis multi-physics rigid-body simulation with CPU/Vulkan backend.
  - Physical hardware bridge over SocketCAN (`can0` @ 1 Mbps) using `piper_sdk`.
  - Bare-hand 3D gesture teleoperation using MediaPipe Tasks API with Synexens CS20 ToF, Intel RealSense, or standard Webcams.
  - Damped Least Squares (DLS) kinematics engine with singularity damping and joint limit projection.
  - Keyboard teleoperation and PySide graphical slider panel.

### Execution Commands:
```bash
cd /home/humble/piper_genesis_project

# 0. Diagnostics (Camera & Environment Preflight)
bash scripts/check_environment.sh
bash scripts/check_camera.sh

# 1. Multi-Physics Genesis Simulation
bash scripts/run_simulation.sh

# 2. Genesis Simulation with Bare-Hand Gesture Teleoperation
bash scripts/run_gesture_simulation.sh
# (Optional) Webcam fallback:
bash scripts/run_gesture_simulation.sh camera:=webcam

# 3. Real Physical Robot Hardware Bridge
bash scripts/run_real_robot.sh

# 4. Bare-Hand Gesture Teleoperation on Physical Hardware
bash scripts/run_gesture_real_robot.sh

# 5. Interactive Control Panels
bash scripts/run_teleop_keyboard.sh  # W/S/A/D/R/F Cartesian teleop
bash scripts/run_teleop_gui.sh       # Graphical slider GUI
bash scripts/launch_rviz.sh          # Standalone RViz viewport

# 6. Verification Test Suite (23 Unit Tests)
.venv/bin/python3 -m pytest tests
```

---

## 4. Bare-Hand Gesture Teleoperation Stack (`piper_gesture_ws`)
* **Path:** `/home/humble/piper_gesture_ws`
* **Key Features:**
  - ROS 2 Humble/Jazzy bare-hand gesture teleoperation port.
  - Synexens CS20 ToF depth/IR camera driver and Intel RealSense D4xx integration.
  - MediaPipe HandLandmarker with palm 3D tracking, 3.0s fist-hold origin calibration, and pinch gripper control.

### Execution Commands:
```bash
conda deactivate
cd /home/humble/piper_gesture_ws
source scripts/env.sh
bash scripts/can_activate.sh can0 1000000
bash scripts/check.sh

# CS20 ToF Camera Dry-Run (No physical arm motion):
ros2 launch piper_gesture_teleop teleop.launch.py cs20_driver:=true dry_run:=true

# CS20 ToF Camera Physical Hardware Execution:
ros2 launch piper_gesture_teleop teleop.launch.py cs20_driver:=true dry_run:=false

# Intel RealSense Camera Launch:
ros2 launch piper_gesture_teleop teleop.launch.py camera:=realsense dry_run:=false
```

---

## 5. Singularity Avoidance & Safety Gate GUI (`PiPER_Physical_Control`)
* **Path:** `/home/humble/PiPER_Physical_Control`
* **Key Features:**
  - 13-point physical safety gate with firmware identity and communication status verification.
  - Standard DH forward kinematics and geometric Jacobian SVD singularity analyzer ($\sigma_{\min}$, $\kappa$, $w$).
  - Fixed-XYZ null-space motion decoupling ($< 0.004\text{ mm}$ drift).
  - PyQt diagnostic and recovery GUI.

### Execution Commands:
```bash
# Launch Singularity Avoidance Platform GUI:
/home/humble/PiPER_Physical_Control/launch_gui.sh

# Passive Feedback & Encoder Freshness Monitor:
source /opt/ros/humble/setup.bash
python3 /home/humble/PiPER_Physical_Control/diagnostics/piper_feedback_monitor.py
```

---

## 6. ROS 2 Kinematics & Null-Space Cartesian Control (`ros2_workspace`)
* **Path:** `/home/humble/ros2_workspace`
* **Packages:** `piper_kinematics`, `piper_singularity`, `piper_fixed_xyz_controller`

### Execution Commands:
```bash
source /opt/ros/humble/setup.bash
source /home/humble/ros2_workspace/install/setup.bash

# Real-time Singularity Metric Publisher:
ros2 launch piper_singularity singularity_monitor.launch.py

# Fixed-XYZ Null-Space Reorientation Controller:
ros2 launch piper_fixed_xyz_controller fixed_xyz_controller.launch.py

# Physical Arm Singularity Evaluation Node:
ros2 launch piper_kinematics physical_piper_singularity.launch.py
```

---

## 7. Official AgileX PiPER Core Stack (`piper_ros`)
* **Path:** `/home/humble/piper_ros`
* **Packages:** `piper`, `piper_description`, `piper_msgs`, `piper_moveit`, `piper_sim`

### Execution Commands:
```bash
source /opt/ros/humble/setup.bash
source /home/humble/piper_ros/install/setup.bash

# Single Arm Driver (SocketCAN can0):
ros2 launch piper start_single_piper.launch.py can_port:=can0

# Driver with Native RViz Visualization:
ros2 launch piper start_single_piper_rviz.launch.py can_port:=can0

# Model & URDF Inspection:
ros2 launch piper_description display_urdf.launch.py

# MoveIt 2 Virtual Demo:
ros2 launch piper_with_gripper_moveit demo.launch.py

# MoveIt 2 on Physical Arm:
ros2 launch piper_with_gripper_moveit piper_moveit.launch.py

# Gazebo Simulation:
ros2 launch piper_gazebo piper_gazebo.launch.py
```

---

## 8. JARVIS-PiPER Embodied AI & PIKA Sense Teleop (`jarvis-piper`)
* **Path:** `/home/humble/robotics/jarvis-piper`
* **GitHub Repository:** `https://github.com/koyaneni-yaswanth/jarvis-piper.git`
* **Key Features:**
  - PIKA Sense 6-DOF spatial tracker teleoperation (SteamVR Lighthouse v2.0).
  - Multimodal observation recording (wrist RealSense D405, overhead camera).
  - V-JEPA visual world models and imitation learning policies (Behavior Cloning & ACT).
  - Automated pre-flight doctor and safety supervisor.

### Execution Commands:
```bash
cd /home/humble/robotics/jarvis-piper

# 1. Preflight Diagnostics:
./scripts/nuc_preflight.sh
./scripts/doctor.sh

# 2. Hardware Checks:
./scripts/diagnose_piper.sh
./scripts/diagnose_pika.sh

# 3. System Launches:
source /opt/ros/humble/setup.bash
ros2 launch jarvis_piper full_system.launch.py  # Full hardware + teleop
ros2 launch jarvis_piper mock.launch.py         # Mock simulation
ros2 launch jarvis_piper rviz_live_display.launch.py # Live display bridge

# 4. Imitation Learning & V-JEPA:
./scripts/record_episode.sh
./scripts/train_vjepa.sh
./scripts/evaluate_vjepa.sh
```

---

## 9. Bimanual PiPER Dual-Arm Manipulation Platform (`bimanual_piper`)
* **Path:** `/home/humble/bimanual_piper`
* **Key Features:**
  - Dual-arm URDF macros and Xacro configuration for coordinated manipulation.
  - MuJoCo physics simulation environment for dual-arm tasks (handover, cooperative lift, bimanual pick-and-place).
  - Coordinated trajectory and safety controllers.

### Execution Commands:
```bash
source /opt/ros/humble/setup.bash
# Visualize Dual-Arm Assembly in RViz2:
ros2 launch bimanual_piper display_bimanual.launch.py

# MuJoCo Physics Simulation:
python3 /home/humble/bimanual_piper/simulation/mujoco/bimanual_sim.py

# Verification Test Suite:
pytest /home/humble/bimanual_piper/tests/
```

---

## 10. Meta Quest VR Teleoperation (`QuestArmTeleop`)
* **Path:** `/home/humble/QuestArmTeleop`
* **Key Features:**
  - Meta Quest 2 / 3 / 3S 6-DOF VR controller teleoperation.
  - ADB USB/Wi-Fi pose streaming via `oculus_reader`.
  - Pinocchio numerical IK solver.

### Execution Commands:
```bash
bash ~/QuestArmTeleop/src/agx_arm_ros/scripts/can_activate.sh
conda activate vt
source ~/QuestArmTeleop/install/setup.bash

# Verify Quest ADB Connection:
adb devices

# Start Single-Arm PiPER Teleoperation:
ros2 launch oculus_reader teleop_single_piper_x.launch.py
```

---

## 11. Standalone Direct Scripts & Verification Utilities

Direct Python tools located in `/home/humble` running without full ROS 2 workspaces:
```bash
# Direct PIKA Sense to PiPER Arm Teleoperation (Zero ROS overhead):
python3 /home/humble/teleop_piper.py

# CAN Link & Cartesian Motion Smoke Test:
python3 /home/humble/piper_smoke_test.py

# Passive Safe Joint State Monitor:
python3 /home/humble/piper_feedback_check.py
```
