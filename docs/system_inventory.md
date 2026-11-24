# System Inventory: JARVIS-PiPER (Target Robot Host)

Generated on: humble-NUC14RVS-B

## 1. Host & Compute Platform
- **Host Name**: `humble-NUC14RVS-B`
- **Operating System**: Ubuntu 22.04.5 LTS (Jammy Jellyfish)
- **Architecture**: x86_64 (Intel Core Ultra 5 125H)
- **System Python Version**: 3.10.12 (`/usr/bin/python3`)
- **Main Project Location**: `~/robotics/jarvis-piper`

## 2. ROS 2 Environment & Workspaces
- **ROS_DISTRO**: humble (ROS 2 Humble Hawksbill)
- **ROS 2 Executable**: `/opt/ros/humble/bin/ros2`
- **Active Workspaces & Control Platforms**:
  - `~/robotics/jarvis-piper`: Embodied AI, V-JEPA & PIKA Sense teleoperation repository
  - `~/PiPER_ROS2_Manipulation`: MoveIt 2 manipulation workstation with C++ `ros2_control` hardware interface & pick-and-place server
  - `~/piper_genesis_project`: Genesis multi-physics simulator digital twin, bare-hand gesture teleop, and keyboard/GUI control
  - `~/piper_gesture_ws`: Bare-hand gesture teleoperation workspace with Synexens CS20 ToF & RealSense
  - `~/PiPER_Physical_Control`: 13-point physical safety gate, DH kinematics & singularity analysis GUI
  - `~/ros2_workspace`: PiPER kinematics, singularity metrics, and fixed-XYZ null-space controller
  - `~/bimanual_piper`: Dual-arm cooperative manipulation framework & MuJoCo physics simulation
  - `~/QuestArmTeleop`: Meta Quest 2/3/3S VR 6-DOF teleoperation workspace
  - `~/piper_ros`: Vendor PiPER ROS 2 driver, URDF description, and simulation workspace
  - `~/pika_ros`: Vendor PIKA teleoperation workspace

## 3. Acceleration & Compute
- **Integrated GPU**: Intel Arc Graphics (Mesa / OpenCL)
- **CUDA Acceleration**: None (CPU inference for policy; ML training on dedicated workstation)

## 4. Robot & Sensor Configuration
- **Robotic Arm**: AgileX PiPER 6-DOF Manipulator (Firmware S-V1.8-8 / S-V1.6-3)
- **Bus Interface**: SocketCAN `can0` configured at 1,000,000 bps (1 Mbps)
- **Convenience Aliases**: `piper_launch`, `piper_recover`, `piper_home` (in `~/.local/bin`)
- **Teleoperators**:
  - AgileX PIKA Sense 6-DoF Handheld Tracker (SteamVR USB Wireless Receiver VID `0x28de`, PID `0x2101`)
  - Meta Quest 2/3/3S VR 6-DOF Handheld Controllers (`oculus_reader`)
  - Bare-hand 3D Gestures (MediaPipe Tasks API)
- **Vision & Depth Sensors**:
  - Synexens CS20 ToF Depth & IR Camera
  - Intel RealSense D405 Sub-Millimeter Depth Camera
  - Intel RealSense D435 / Depth series
  - Overhead DECXIN / Sunplus USB RGB Camera
- **Optical Base Stations**: 2x PIKA Stations (HTC Vive Lighthouse Base Stations v2.0)
- **Auxiliary Serial**: CH341 USB-to-Serial Adapter (`/dev/ttyUSB0`)
