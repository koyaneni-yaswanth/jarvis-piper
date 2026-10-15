# JARVIS-PiPER: Demonstration Dataset & Recordings Inventory

**Date:** October 15, 2026  
**Auditor:** JARVIS Systems Architecture Lead  
**Scope:** Verified Physical Demonstrations & Fixture Datasets on NUC Storage

---

## 1. Discovered Real Demonstration Episodes

All original raw demonstrations are preserved outside of Git in `/home/humble/pika_mgat_files/`.

### 1.1 Canonical Raw MCAP Recordings (`episodes/`)
Total count: **20 recorded episodes** | Total size: **2.1 GB**

| File Name | File Size | Modality / Topics Present | Recording Date | Status |
| :--- | :---: | :--- | :--- | :---: |
| `episode_0000.mcap` | 122 MB | Color, Depth, Fisheye, Pose, Gripper, Encoder, TF | 2026-08-31 | VERIFIED |
| `episode_0001.mcap` | 96 MB | Color, Depth, Fisheye, Pose, Gripper, Encoder, TF | 2026-08-31 | VERIFIED |
| `episode_0002.mcap` | 480 MB | Color, Depth, Fisheye, Pose, Gripper, Encoder, TF | 2026-08-31 | VERIFIED |
| `episode_0003.mcap` | 95 MB | Color, Depth, Fisheye, Pose, Gripper, Encoder, TF | 2026-08-31 | VERIFIED |
| `episode_0004.mcap` | 128 MB | Color, Depth, Fisheye, Pose, Gripper, Encoder, TF | 2026-08-31 | VERIFIED |
| `episode_0005.mcap` | 153 MB | Color, Depth, Fisheye, Pose, Gripper, Encoder, TF | 2026-09-03 | VERIFIED |
| `episode_0006.mcap` | 5.8 MB | Color, Depth, Fisheye, Pose, Gripper, Encoder, TF | 2026-09-03 | VERIFIED (Short) |
| `episode_0007.mcap` | 101 MB | Color, Depth, Fisheye, Pose, Gripper, Encoder, TF | 2026-09-03 | VERIFIED |
| `episode_0008.mcap` | 83 MB | Color, Depth, Fisheye, Pose, Gripper, Encoder, TF | 2026-09-03 | VERIFIED |
| `episode_0009.mcap` | 83 MB | Color, Depth, Fisheye, Pose, Gripper, Encoder, TF | 2026-09-03 | VERIFIED |
| `episode_0010.mcap` | 100 MB | Color, Depth, Fisheye, Pose, Gripper, Encoder, TF | 2026-09-03 | VERIFIED |
| `episode_0011.mcap` | 72 MB | Color, Depth, Fisheye, Pose, Gripper, Encoder, TF | 2026-09-03 | VERIFIED |
| `episode_0012.mcap` | 47 MB | Color, Depth, Fisheye, Pose, Gripper, Encoder, TF | 2026-09-03 | VERIFIED |
| `episode_0013.mcap` | 75 MB | Color, Depth, Fisheye, Pose, Gripper, Encoder, TF | 2026-09-03 | VERIFIED |
| `episode_0014.mcap` | 82 MB | Color, Depth, Fisheye, Pose, Gripper, Encoder, TF | 2026-09-04 | VERIFIED |
| `episode_0015.mcap` | 14 MB | Color, Depth, Fisheye, Pose, Gripper, Encoder, TF | 2026-09-05 | VERIFIED |
| `episode_0016.mcap` | 69 MB | Color, Depth, Fisheye, Pose, Gripper, Encoder, TF | 2026-09-05 | VERIFIED |
| `episode_0017.mcap` | 108 MB | Color, Depth, Fisheye, Pose, Gripper, Encoder, TF | 2026-09-05 | VERIFIED |
| `episode_0018.mcap` | 97 MB | Color, Depth, Fisheye, Pose, Gripper, Encoder, TF | 2026-09-05 | VERIFIED |
| `episode_0019.mcap` | 86 MB | Color, Depth, Fisheye, Pose, Gripper, Encoder, TF | 2026-09-09 | VERIFIED |

---

## 2. Converted HDF5 Dataset Artifact (`hdf5/episode_0003.hdf5`)

- **File Path:** `/home/humble/pika_mgat_files/hdf5/episode_0003.hdf5`
- **File Size:** 356 MB
- **Duration:** 11.60 seconds | Total Frames: 349 @ 30.00 FPS (mean dt 33.3 ms)
- **Timestamp Jitter:** 0.1 ms (stable clock synchronization)

### 2.1 Internal Array Architecture

```text
/action                           (349, 8)             float32
/observations/images/color        (349, 480, 640, 3)   uint8
/observations/images/depth        (349, 480, 640)      uint16
/observations/images/fisheye      (349, 480, 640, 3)   uint8
/observations/qpos                (349, 8)             float32
/timestamps                       (349,)               float64
```

### 2.2 Mathematical Quality Validation
1. **Action Alignment:**
   - Evaluated condition: $\max |a[t] - q[t+1]|$
   - Measured error: `0.00e+00` (perfect 1-step forward prediction alignment)
2. **Quaternion Unit Norm:**
   - Evaluated condition: $\min \|\mathbf{q}\| \dots \max \|\mathbf{q}\|$
   - Measured range: `1.0000 .. 1.0000` (valid unit norm, zero distortion)
3. **Sensor Travel Spans:**
   - Cartesian Travel: X: [-0.360, -0.174], Y: [0.612, 0.896], Z: [-0.102, 0.404] (Total travel: 2.46 m)
   - Gripper Trigger: 9.80 mm to 98.56 mm (Span: 88.76 mm)
4. **Depth Stream Authenticity:**
   - Valid non-zero pixels: 70.7% to 76.5%
   - Unit scale: $1.0 \times 10^{-4}$ m/unit (D405 calibrated depth profile)
