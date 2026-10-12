# NVIDIA Isaac Sim & Isaac Lab Integration Guide

**Platform:** NVIDIA Isaac Sim 4.2+ / Isaac Lab  
**Manipulator:** AgileX PiPER 6-DOF + Two-Finger Parallel Gripper  
**GPU Target:** NVIDIA RTX 5060 (8GB VRAM) | Driver 591.86 | CUDA 13.1  

---

## 1. System Compatibility & Environment Isolation

Isaac Sim requires NVIDIA Omniverse and Python 3.10 with specialized PyTorch/CUDA libraries. To prevent library conflicts between **ROS 2 Lyrical** and **Isaac Sim**:

> [!IMPORTANT]
> **Strict Environment Isolation:**
> Never install Isaac Sim directly into the system ROS 2 Python environment.
> Run Isaac Sim inside its dedicated conda environment or official Docker container:
> ```bash
> docker run --name isaac-sim --entrypoint bash -it --gpus all \
>   -v "D:/yaswanth/ranger mini/jarvis-piper:/workspace/jarvis-piper" \
>   nvcr.io/nvidia/isaac-sim:4.2.0
> ```

---

## 2. Health & Hardware Verification

Run the dedicated Isaac Sim diagnostic doctor:

```bash
python scripts/isaac/isaac_doctor.py
```

This verifies:
1. NVIDIA GPU presence and VRAM capacity ($8151\text{ MiB}$ on RTX 5060).
2. NVIDIA display driver compatibility ($\ge 535.129$).
3. PyTorch CUDA tensor acceleration.
4. Omniverse installation paths.

---

## 3. Digital Twin Asset Pipeline: URDF to USD

The authoritative PiPER URDF (`ros2_ws/src/jarvis_piper_bringup/urdf/piper.urdf`) is compiled into an Isaac Articulation USD asset using:

```bash
python scripts/isaac/urdf_to_usd.py --urdf ros2_ws/src/jarvis_piper_bringup/urdf/piper.urdf --output models/usd/piper.usda
```

### Generated USD Properties:
* **Root Prim:** `/World/Piper`
* **Articulation API:** `PhysicsArticulationRootAPI`
* **Drive Stiffness ($k_p$):** $400.0\text{ N}\cdot\text{m/rad}$
* **Drive Damping ($k_d$):** $40.0\text{ N}\cdot\text{m}\cdot\text{s/rad}$
* **Max Force Limits:** $100.0\text{ N}\cdot\text{m}$ on joints 1–6, $10.0\text{ N}$ on fingers 7–8.

---

## 4. Headless Articulation & Physics Verification

Before launching multi-GPU training or complex environments, validate physics stability and reset determinism in headless mode:

```bash
python scripts/isaac/test_isaac_headless.py
```

### Verified Acceptance Criteria:
* Zero NaN / Inf excursions across all 6 revolute joints.
* PD controller reaches target joint setpoint within $100$ simulation steps ($< 0.05$ rad tracking error).
* Observation tensor contract matches the 16-dimensional physical state vector ($q_{1..6}, \dot{q}_{1..6}, p_{\text{tcp}}, \text{stroke}$).

---

## 5. Task Environments

Two task environments are configured in `configs/`:

1. **Target Reaching Skill (`configs/isaac_piper_reach.yaml`):**
   * Parallel environments: $128$
   * Control frequency: $50\text{ Hz}$ ($dt = 0.02\text{ s}$)
   * Physics frequency: $200\text{ Hz}$ ($dt = 0.005\text{ s}$)
   * Observation: $16\text{D}$ state vector $+ 3\text{D}$ target position ($19\text{D}$ total).
   * Reward: Shaped Euclidean distance to goal $+ 50.0$ terminal reach bonus.

2. **Autonomous Pick-and-Place (`configs/isaac_piper_pick_place.yaml`):**
   * Parallel environments: $64$
   * Objects: Rigid cube ($40\text{ mm}$, $50\text{ g}$) and destination tray.
   * Reward: Approach bonus $+$ Grasp contact bonus $+$ Lift height bonus $+$ Placement bonus.

---

## 6. Sim-to-Real Transfer & Observation Pipeline Isolation

To prevent simulation artifacts from degrading real physical robot performance:

1. **Zero Simulation Ground-Truth Leakage:**
   * Policies must never ingest ground-truth object poses or collision distances directly from the physics simulator.
   * Observations must strictly utilize estimated visual poses (from overhead/wrist cameras) and proprioceptive joint telemetry.
2. **Action Filtering & Smoothing:**
   * Action outputs are delta joint targets scaled by $\Delta q \le 0.05$ rad.
   * Pass through the `SafetySupervisor` before dispatching to the physical arm controller.
