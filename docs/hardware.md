# Hardware Integration & Wiring Reference

This document outlines electrical, mechanical, and bus connections for the **AgileX PIKA Sense** and **PiPER 6-DOF robotic manipulator**.

---

## 1. Hardware Bill of Materials (BOM)

| Component | Specification | Connection Interface | Default Device / Topic |
|---|---|---|---|
| **PiPER Robotic Arm** | 6-DOF Lightweight Manipulator | CAN-bus (1 Mbps, CAN 2.0B) | `can0` / socketCAN |
| **PIKA Gripper** | 2-Finger Parallel Jaw (0-35mm stroke) | Internal PiPER CAN Bus | `/piper/gripper/ctrl` |
| **PIKA Sense Station** | Optical 6-DOF Master Controller | USB 3.0 Type-C | `/pika_pose` |
| **Wrist Camera** | USB RGB/Depth (720p @ 30fps) | USB 3.0 Type-A | `/dev/video0` (`/camera`) |
| **Stationary Base Camera**| Fixed Overhead/Side Camera | USB 3.0 Type-A | `/dev/video2` (`/camera/base`) |
| **Power Supply** | 24V DC / 10A (PiPER base) | 2-pin Aviation Connector | Power Jack |

---

## 2. CAN-Bus Setup & SocketCAN Configuration

The PiPER arm communicates via high-speed CAN (1 Mbps). Connect the CAN adapter (e.g. Waveshare USB-CAN or Candlelight) and bring up the network interface:

```bash
# Set bitrate to 1000000 (1 Mbps) and bring up can0
sudo ip link set can0 type can bitrate 1000000
sudo ip link set up can0

# Verify CAN interface status
ip -details link show can0
```

To enable persistence across reboots, add to `/etc/network/interfaces` or systemd network units:
```ini
allow-hotplug can0
iface can0 can static
    bitrate 1000000
    up ifconfig $IFACE txqueuelen 1000
```

---

## 3. PIKA Sense Teleoperation Connection

The PIKA Sense master controller provides 6-DOF Cartesian poses and gripper trigger signals.
- Connect the PIKA base station via USB 3.0 to the host PC.
- Standard AgileX driver scripts in `~/pika_ros/` launch the publisher node:
  ```bash
  # Standard AgileX launcher
  bash ~/pika_ros/start_single_sensor_whit_teleop.bash
  ```
- JARVIS-PiPER automatically listens to the resulting `/pika_pose` and `/pika_teleop_status` topics.

---

## 4. Safety Emergency Stop (E-Stop)

- Ensure the hardware emergency stop button is mounted within reach of the operator.
- PiPER firmware enforces motor torque cut-off upon receiving CAN emergency packet or watchdog timeout ($>100\text{ ms}$ communication gap).
- Software E-stop can be triggered via ROS 2:
  ```bash
  ros2 topic pub --once /piper/estop std_msgs/msg/Bool "{data: true}"
  ```
