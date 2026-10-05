# Simulation Mode (Gazebo Harmonic & Isaac Sim)

Simulation Mode enables closed-loop testing, synthetic demonstration generation, and reinforcement learning without hardware wear or collision risks.

---

## 1. Supported Simulators

1. **Gazebo Harmonic (ROS 2 Lyrical Native)**:
   - Uses DART / Bullet physics engine.
   - Communicates via `gz_ros2_control` hardware interfaces.
   - Simulates PiPER arm joints, gripper effort contacts, and wrist RGBD camera sensors.
2. **NVIDIA Isaac Sim / Omniverse**:
   - High-fidelity ray-traced rendering and GPU-accelerated PhysX.
   - Useful for domain randomization and vision model pretraining.

---

## 2. Launching Simulation Mode

To launch the full simulation pipeline:

```bash
ros2 launch jarvis_piper_bringup simulation.launch.py
```

Or using the unified top-level launcher:

```bash
ros2 launch launch/full_system.launch.py mode:=simulation
```

---

## 3. Simulated Topics

Simulation mode exposes identical topic interfaces as real hardware:
- `/piper/joint_states`
- `/piper/joint_trajectory_controller/joint_trajectory`
- `/camera`
- `/camera/depth_image`
- `/pika_pose` (synthesized from virtual leader or gamepad)
