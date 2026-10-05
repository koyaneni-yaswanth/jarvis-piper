# Dataset Replay Mode (Passive Playback)

Dataset Replay Mode reads previously recorded demonstration episodes and streams them across ROS 2 topics at original recording speeds without sending motor commands.

---

## 1. Safety & Non-Actuation Guarantee

In Replay Mode:
- **Zero Actuation Commands**: The node **never** publishes to `/piper/command` or sends CAN actuation frames.
- **Passive Feedback Topics**: Frames are re-published strictly onto state and monitoring topics:
  - `/piper/joint_states`
  - `/piper_teleop/joint_states`
  - `/pika_pose`
  - `/camera`
- This ensures recorded demonstrations can be safely inspected, visualized in RViz, and fed into perception pipelines in lab environments without risk of unexpected arm movement.

---

## 2. Replay via CLI

```bash
jarvis-piper replay dataset/raw/ep_demo_001_20261005_120000
```

---

## 3. Replay via ROS 2 Launch

```bash
ros2 launch jarvis_piper_bringup replay.launch.py episode_path:=dataset/raw loop:=true playback_rate:=50.0
```
Parameters:
- `episode_path`: Path to an episode folder or root dataset folder.
- `playback_rate`: Replay speed in Hz (default 50.0).
- `loop`: If `true`, continuously restarts playback when the episode completes.
