# PIKA Sense Teleoperation System

The **AgileX PIKA Sense** is a handheld optical tracking controller designed for intuitive 6-DOF leader-follower teleoperation.

---

## 1. Operating Principle

The PIKA Sense controller tracks position ($x, y, z$) and orientation (quaternion $x, y, z, w$) in a reference optical tracking volume relative to its base station. The controller also features an analog trigger paddle representing the gripper stroke ($0.0$ to $1.0$).

---

## 2. ROS 2 Interface & Topic Mapping

| Sensor Output | ROS 2 Topic | Message Type | Frequency |
|---|---|---|---|
| Master Hand Pose | `/pika_pose` | `geometry_msgs/msg/PoseStamped` | 50 Hz |
| Trigger / Gripper | `/pika_gripper_cmd` | `std_msgs/msg/Float32` | 50 Hz |
| Teleop State & Buttons | `/pika_teleop_status` | `jarvis_piper_interfaces/msg/PikaTeleopStatus` | 20 Hz |

---

## 3. AgileX Driver Integration

JARVIS-PiPER maintains full backward compatibility with the official AgileX scripts in `~/pika_ros/`:
- `start_single_sensor_whit_teleop.bash`: Launches base sensor node and teleop mapping.
- `teleop_single_piper.launch.py`: Computes differential Cartesian IK and sends CAN joint targets to the PiPER arm.

When running in **REAL HARDWARE MODE**, JARVIS-PiPER passively subscribes to the outputs of these nodes, ensuring zero interference with validated vendor control loops while capturing synchronized telemetry.

In **MOCK MODE**, `MockPikaSenseAdapter` simulates smooth minimum-jerk optical poses and trigger movements for seamless offline testing.
