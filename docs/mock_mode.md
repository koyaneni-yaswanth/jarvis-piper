# Mock Data Mode & Zero-Hardware Development

Mock Data Mode is the primary development and CI/CD mechanism of JARVIS-PiPER. It allows full repository installation, testing, validation, export, and model pretraining on machines without physical robot arms, CAN adapters, or cameras.

---

## 1. How Mock Mode Works

When Mock Mode is enabled:
1. `MockPiperAdapter` simulates a smooth 6-DOF joint trajectory completing representative manipulation tasks (e.g. pick and place).
2. `MockCameraAdapter` generates synthetic animated RGB and depth frames with moving color cues.
3. `MockPikaSenseAdapter` streams optical controller poses matching the arm's trajectory.
4. The ROS 2 Time Synchronizer and Episode Recorder operate identically to hardware mode, logging full-fidelity episodes.

---

## 2. Generating Synthetic Demonstrations via CLI

Generate $N$ mock demonstration episodes with a single command:

```bash
jarvis-piper demo --episodes 5 --steps 120 --output-dir dataset/raw
```

Each generated episode includes:
- `metadata.json`
- `trajectory.json`
- `stream_journal.jsonl`
- `camera_wrist.mp4`
- Keyframe image snapshots in `images/wrist/` and `images/depth/`

---

## 3. Launching Mock Mode under ROS 2

```bash
ros2 launch jarvis_piper_bringup mock.launch.py
```
This spawns:
- `pika_piper_mock_streamer` (publishes mock telemetry at $50\text{ Hz}$ and camera at $30\text{ Hz}$)
- `time_synchronizer_node` (aligns topics)
- `recorder_node` (ready for `StartEpisode` / `StopEpisode` triggers)
