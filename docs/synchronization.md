# Multimodal Time Synchronization & Ring Buffering

Achieving high-quality robot interaction datasets requires precise temporal alignment between high-rate arm state feedback ($50\text{--}100\text{ Hz}$) and camera visual frames ($30\text{ Hz}$).

---

## 1. Challenge & Problem Statement

- PiPER arm publishes joint states at $50\text{ Hz}$ or $100\text{ Hz}$.
- PIKA Sense controller streams poses at $50\text{ Hz}$.
- RGB and Depth cameras publish at $30\text{ FPS}$ with varying USB capture latencies ($10\text{--}25\text{ ms}$).
- Unaligned frames produce policy errors where the robot's observed state is delayed relative to what the camera saw, causing behavioral cloning models to oscillate or miss grasps.

---

## 2. Synchronization Architecture

JARVIS-PiPER implements a zero-copy **Time Synchronizer** (`jarvis_piper_sync`):

```
 Joint States (50Hz) ──────► Ring Buffer 1 (Capacity 100) ──┐
                                                            │  Adaptive Slop
 Optical Poses (50Hz) ─────► Ring Buffer 2 (Capacity 100) ──┼─► Pair Search ──► SynchronizedFrame
                                                            │  (dt <= 30ms)     (Emitted at 50Hz)
 Camera Frames (30Hz) ─────► Ring Buffer 3 (Capacity 60)  ──┘
```

### Key Mechanisms:
1. **Thread-Safe Ring Buffer**: Circular buffers store recent history without dynamic memory allocation spikes.
2. **Adaptive Slop Matching**: Matches each master telemetry frame with the temporally nearest camera frame within a configured window (default $\pm 30\text{ ms}$).
3. **Linear State Interpolation**: If telemetry rates diverge, robot positions and velocities are smoothly interpolated to the exact camera optical shutter timestamp.
4. **Jitter Monitoring**: Constantly records timestamp variance and alerts the operator if USB bus contention causes frame drops.
