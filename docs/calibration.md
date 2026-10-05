# Calibration & Coordinate Frame Registration

Accurate coordinate transformations between the robot base, camera optical centers, and PIKA Sense controller are required for spatial world modeling and visual servoing.

---

## 1. Coordinate Frames Hierarchy

```
                    world
                      │
              ┌───────┴───────┐
              ▼               ▼
         piper_base_link    pika_base
              │
          joint1..6
              │
          wrist_mount
              │
      ┌───────┴───────┐
      ▼               ▼
   camera_link     piper_tcp
```

- `piper_base_link`: Physical base plate of the PiPER arm (origin of robot kinematics).
- `pika_base`: Optical tracking station base coordinate frame.
- `camera_link`: Wrist camera optical frame ($Z$ forward, $X$ right, $Y$ down).
- `piper_tcp`: Tool Center Point between the parallel gripper fingers.

---

## 2. Hand-Eye Calibration (Eye-in-Hand)

To register the wrist camera pose relative to the end-effector:
1. Place an AprilTag or checkerboard target on the workbench.
2. Record $N \ge 12$ diverse robot poses observing the calibration target from different pitch, roll, and elevation angles.
3. Solve the classical $AX = XB$ hand-eye calibration problem using Tsai-Lenz or Park-Martin algorithms.
4. Store the resulting $4 \times 4$ homogeneous transform in `configs/calibration.yaml`.

---

## 3. PIKA-to-Arm Frame Mapping

The PIKA Sense controller provides raw poses in `pika_base` coordinates. 
The adapter applies rotation mapping $R_{\text{pika}\rightarrow\text{arm}}$ and translation scaling:
$$p_{\text{target}} = p_{\text{home}} + S \cdot R_{\text{pika}\rightarrow\text{arm}} \cdot (p_{\text{sense}} - p_{\text{origin}})$$
where $S$ is a sensitivity scaling factor (default $1.0$).
