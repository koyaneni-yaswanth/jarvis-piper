# System Inventory: JARVIS-PiPER (Target Robot Host)

Generated on: humble-NUC14RVS-B

## 1. Host & Compute Platform
- **Host Name**: `humble-NUC14RVS-B`
- **Operating System**: Ubuntu 22.04.5 LTS (Jammy Jellyfish)
- **Architecture**: x86_64 (Intel Core Ultra 5 125H)
- **System Python Version**: 3.10.12 (`/usr/bin/python3`)
- **Main Project Location**: `~/robotics/jarvis-piper`

## 2. ROS 2 Environment
- **ROS_DISTRO**: humble (ROS 2 Humble Hawksbill)
- **ROS 2 Executable**: `/opt/ros/humble/bin/ros2`
- **ROS Workspaces**:
  - `~/piper_ros`: Vendor PiPER ROS 2 driver workspace
  - `~/pika_ros`: Vendor PIKA teleoperation workspace
  - `~/ros2_ws`: JARVIS-PiPER integrated ROS 2 workspace

## 3. Acceleration & Compute
- **Integrated GPU**: Intel Arc Graphics (Mesa / OpenCL)
- **CUDA Acceleration**: None (CPU inference for policy; ML training on dedicated workstation)

## 4. Robot & Sensor Configuration
- **Robotic Arm**: AgileX PiPER 6-DOF Manipulator (Firmware S-V1.6-3)
- **Bus Interface**: SocketCAN `can0` configured at 1,000,000 bps (1 Mbps)
- **Teleoperator**: AgileX PIKA Sense 6-DoF Handheld Tracker
- **Tracking Receivers**: SteamVR USB Wireless Receiver (VID `0x28de`, PID `0x2101`)
- **Optical Base Stations**: 2x PIKA Stations (HTC Vive Lighthouse Base Stations)
- **Wrist Camera**: Intel RealSense D405 Sub-Millimeter Depth Camera
- **Overhead Camera**: DECXIN / Sunplus USB RGB Camera
- **Auxiliary Serial**: CH341 USB-to-Serial Adapter (`/dev/ttyUSB0`)
