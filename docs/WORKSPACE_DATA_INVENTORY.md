# JARVIS-PiPER: Workspace Data Inventory & V-JEPA Readiness Analysis

**Generated On:** October 2026  
**Tool:** `scripts/collect_robot_workspace_data.py`  
**Total Identified Files:** 5,159 files across 13 candidate search roots  
**Archived in:** `workspace_data_collection/` (`inventory.csv` & `collection_summary.json`)

---

## 1. Executive Summary & Category Breakdown

The automated workspace data inventory scanned all local drives and WSL Linux environments (`Ubuntu-22.04` and `Ubuntu-26.04`) to establish what robot telemetry, visual streams, models, and configurations currently exist.

| Category Tag | File Count | Domain & File Types | Primary Locations |
| :--- | :--- | :--- | :--- |
| **`DIAGNOSTICS_LOG`** | 1,743 | Execution logs, test traces, benchmark outputs (`.log`, `.txt`, `.out`) | `ranger_mini_lyrical_ws`, `robotics_platform` |
| **`PYTHON_SOURCE`** | 949 | Core robotics packages, drivers, algorithms (`.py`) | `jarvis-piper`, `jarvis_piper_ws`, `lerobot` |
| **`SHELL_SCRIPT`** | 523 | Bringup, doctor, build, and diagnostic scripts (`.sh`) | `ranger_mini_lyrical_2604_project/scripts` |
| **`PERCEPTION_IMAGE`** | 339 | Labeled RGB images for object detection (`.jpg`, `.png`) | `Jarvis_Object_Detection.v1i.yolov11` |
| **`PERCEPTION_CONFIG`**| 285 | Roboflow annotations, bounding boxes, labels (`.yaml`, `.txt`) | `Jarvis_Object_Detection.v1i.yolov11` |
| **`DOCUMENTATION`** | 251 | Architecture specs, operation manuals, user guides (`.md`, `.pdf`) | `docs/`, `ROBOTIC ARM/`, root directories |
| **`ROS_LAUNCH_FILE`** | 128 | ROS 2 system launch pipelines (`.launch.py`, `.xml`) | `ranger_bringup`, `jarvis_piper_bringup` |
| **`SYSTEM_CONFIG`** | 121 | ROS 2, MoveIt 2, and package YAML configs (`.yaml`) | `configs/`, `ranger_control/config/` |
| **`ROBOT_URDF`** | 75 | Kinematic model descriptions (`.urdf`, `.xacro`) | `jarvis_piper_bringup/urdf`, `ranger_description` |
| **`ROBOT_CAD_MESH`** | 54 | 3D mesh assets and CAD files (`.stl`, `.step`, `.3mf`) | `ROBOTIC ARM/`, `ranger_description/meshes` |
| **`LEARNING_CHECKPOINT`**| 53 | Neural network weights, policies, ONNX models (`.pt`, `.onnx`) | `models/checkpoints/`, `models/exported/` |
| **`VJEPA_VISION_VIDEO`**| 38 | Video sequences and camera streams (`.mp4`, `.avi`) | `dataset/raw/`, `ROBOTIC ARM/`, `videos/` |
| **`VJEPA_DEPTH_STREAM`**| 16 | 16-bit depth observation frames (`.png`) | `dataset/raw/ep_*/images/depth/` |
| **`ARCHIVE_DATA`** | 16 | Project archives, CAD zips, benchmark packages (`.zip`) | `ROBOTIC ARM/`, `ranger mini/` |
| **`PIPER_TELEMETRY`** | 12 | Synchronized joint & action logs (`.jsonl`, `.json`, `.npz`) | `dataset/raw/`, `dataset/exports/` |
| **`PIKA_DOCUMENTATION`**| 11 | Official AgileX PIKA Sense & Station user manuals (`.md`) | `Pika Product User Manual beta（EN）ROS2.md` |
| **`MOVEIT_SRDF`** | 8 | MoveIt 2 semantic descriptions & collision matrices (`.srdf`) | `ranger_manipulation/config/ranger_piper.srdf` |
| **`PIKA_TELEOP_CONFIG`**| 3 | SteamVR udev rules, tracking configs (`81-vive.rules`) | `configs/pika.yaml`, `udev/` |
| **`PERCEPTION_WEIGHTS`**| 3 | Pretrained YOLO11 object detection weights (`yolo11n.pt`) | `Jarvis_Object_Detection.v1i.yolov11/yolo11n.pt` |

---

## 2. Research Classification for V-JEPA & Embodied AI

### 2.1 V-JEPA 2 & Action-Conditioned V-JEPA 2-AC (Visual World Modeling)
- **What Exists:**
  - 38 video sequences (`wrist.mp4`) recording Piper arm end-effector and camera perspectives.
  - 16 depth streams providing 16-bit depth maps aligned with RGB frames.
  - 339 high-resolution images from `Jarvis_Object_Detection.v1i.yolov11` with tabletop objects (`red block`, `bowl`, `cup`).
  - ViT Spatio-Temporal Patch Embedding ($2\times 16\times 16$ 3D convolution) and Latent Predictor with action-conditioning in `python/world_model/vjepa/model.py`.
- **What is Needed:**
  - Broad spatial visual rollouts covering varied arm reaching trajectories across the entire $626\,\text{mm}$ spherical envelope.
  - Multi-scene lighting and tabletop arrangement variations for visual invariance pretraining.

### 2.2 Piper 6-DOF Telemetry & Policy Learning
- **What Exists:**
  - `stream_journal.jsonl` line-by-line low-latency telemetry (joint positions $q_1..q_6$, velocities $\dot{q}$, efforts $\tau$, gripper stroke, TCP pose).
  - Multi-format exporters (`python/dataset/exporters.py`) converting logs to Hugging Face LeRobot v2.0, ALOHA HDF5, and RLDS.
  - Trained imitation policies: Behavioral Cloning (`bc_piper_policy.pt`) and Action Chunking Transformer (`act_piper_policy.pt`).
  - MoveIt 2 configuration `ranger_piper.srdf` with verified planning groups (`piper_arm`, `piper_gripper`).
- **What is Needed:**
  - Real SocketCAN (`can0`) teleoperation demonstration bags collected once physical hardware is energized.

### 2.3 Pika Sense & Teleoperation Hub
- **What Exists:**
  - SteamVR wireless USB receiver rules (`81-vive.rules`, VID `0x28de`).
  - HTC Vive lighthouse tracking specification in `Pika Product User Manual beta（EN）ROS2.md`.
  - 2nd-order Butterworth low-pass filter ($12\,\text{Hz}$) for hand tremor rejection.
  - E-Stop dead-man clutch logic in `scripts/teleoperation_test.py`.
- **What is Needed:**
  - Lighthouse base station physical in-room calibration (`~/.config/libsurvive/config.json`) once deployed in the laboratory.

### 2.4 Perception & Object Grounding
- **What Exists:**
  - Fine-tuned YOLO11 model weights: `yolo11n.pt` located at `D:\yaswanth\ranger mini\Jarvis_Object_Detection.v1i.yolov11\yolo11n.pt`.
  - Annotated Roboflow dataset for classes: `['bowl', 'cup', 'red block']`.
  - Integrated 3D pinhole camera deprojection in `python/jarvis_piper/perception/detector.py`.
- **What is Needed:**
  - Physical camera extrinsic calibration ($T_{\text{robot}\leftarrow\text{cam}}$) using an ArUco board on the workbench.

---

## 3. The 3 Core Research Starter Themes (Action Plan)

To transition from synthetic prototyping to physical research benchmarks, data collection is structured into the 3 core starter themes:

```mermaid
flowchart TD
    subgraph Theme1 ["Theme 1: Pick and Place"]
        T1_Approach["Pre-Grasp Approach (+8cm)"] --> T1_Grasp["Gripper Closure (12mm)"]
        T1_Grasp --> T1_Lift["Vertical Lift (+16cm)"]
        T1_Lift --> T1_Transport["Transport to Bowl"]
        T1_Transport --> T1_Release["Release & Home"]
    end

    subgraph Theme2 ["Theme 2: Visual Prediction (V-JEPA 2-AC)"]
        T2_Rollout["Multi-Sine Reaching Motions"] --> T2_Persp["Perspective & Lighting Variations"]
        T2_Persp --> T2_Action["Paired Action Vector a_t in R^7"]
        T2_Action --> T2_Latent["Predictor Loss ||p(z) - g(z)||_1"]
    end

    subgraph Theme3 ["Theme 3: Failure Detection & Recovery"]
        T3_Slip["Grasp Slip Anomaly (0.00m)"] --> T3_Detect["Slip Contact Failure Flagged"]
        T3_Detect --> T3_Backoff["Open Gripper & Back-off +5cm"]
        T3_Backoff --> T3_Regrasp["Re-Approach & Secure Grasp"]
        T3_Regrasp --> T3_Complete["Resume Transport & Placement"]
    end
```

### Generation & Validation Target
Run the thematic generator on the workstation:
```bash
python python/jarvis_piper/cli/main.py demo --theme all --episodes 5 --output-dir dataset/raw
```
This produces 15 high-fidelity episodes (5 per core theme) with complete synchronized video, 16-bit depth, joint states, actions, and metadata.
