# Sensors and Multi-Camera Setup

Multimodal robot learning requires diverse visual perspectives to eliminate occlusions and provide rich spatial representations.

---

## 1. Camera Configurations

JARVIS-PiPER supports multi-view camera streams:

| Camera Role | Mount Location | Resolution | Framerate | ROS 2 Topic |
|---|---|---|---|---|
| **Wrist Camera** | PiPER End-Effector / Forearm | $640 \times 480$ RGB | 30 FPS | `/camera` (`/camera/color/image_raw`) |
| **Depth Stream** | PiPER End-Effector / Forearm | $640 \times 480$ 16-bit Depth | 30 FPS | `/camera/depth_image` |
| **Base / Overhead** | Fixed Table Mount | $640 \times 480$ RGB | 30 FPS | `/camera/base/color/image_raw` |

---

## 2. Image Compression & Storage Formats

To ensure real-time recording without disk I/O bottlenecks:
1. **Video Streaming**: Video frames are encoded on-the-fly to H.264/MP4 (`camera_wrist.mp4`) via hardware-accelerated OpenCV VideoWriter or libx264.
2. **Keyframe Snaps**: High-resolution lossless snapshots (JPEG for RGB, 16-bit PNG for Depth) are saved every $N$ frames in `images/wrist/` and `images/depth/`.
3. **Timestamp Alignment**: Frame sequence numbers are strictly indexed with millisecond timestamps and matched to the active robot telemetry timestep in `stream_journal.jsonl`.
