# Public Internet Robot-Learning Dataset & Pretrained Model Audit

**Audit Date:** 2026-10-12  
**Purpose:** Evaluate open-access robotics datasets, demonstration libraries, and foundation model checkpoints for pretraining, policy initialization, and representation learning for the AgileX PiPER 6-DOF manipulator.

---

## 1. Summary Compatibility Matrix

| Dataset / Model | Official Source | License | Embodiment | Action Representation | Compatibility Status | Role in JARVIS-PiPER |
|:---|:---|:---|:---|:---|:---|:---|
| **Hugging Face LeRobot** (`aloha_mobile_cabinet`, `pusht`) | [hf.co/lerobot](https://huggingface.co/lerobot) | Apache 2.0 / MIT | Bimanual ALOHA / Planar pusher | Joint positions $(N \times 14)$ / $(2)$ | `CONVERTIBLE_WITH_VALIDATION` | ACT / Diffusion Policy fine-tuning baseline |
| **Open X-Embodiment (OXE)** | [Google / Embodied-AI Consortium](https://robotics-transformer-x.github.io/) | CC-BY 4.0 | 22+ Embodiments (Franka, UR5, WidowX) | Delta EEF $(x,y,z,r,p,y,\text{grip})$ | `PRETRAINING_ONLY` | Visual prior pretraining & world model representation |
| **ALOHA / Stanford ACT** | [tonyzhaozh/act](https://github.com/tonyzhaozh/act) | MIT | Bimanual ViperX 300 6-DOF | Absolute joint positions $(14)$ | `CONVERTIBLE_WITH_VALIDATION` | Action Chunking with Transformers architecture reference |
| **DROID** | [droid-dataset.github.io](https://droid-dataset.github.io/) | CC-BY 4.0 | Franka Emika Panda 7-DOF | Delta EEF pose + gripper | `PRETRAINING_ONLY` | Large-scale visual manipulation pretraining |
| **RoboMimic** (`can`, `lift`, `square`) | [robomimic.github.io](https://robomimic.github.io/) | MIT | Franka Panda / Sawyer | Joint / EEF OSC positions | `EVALUATION_ONLY` | Benchmark algorithm comparison (BC, BC-RNN, Diffusion) |
| **LIBERO Benchmark** | [Lifelong-Robot-Learning/LIBERO](https://github.com/Lifelong-Robot-Learning/LIBERO) | MIT | Franka Panda (Simulated MuJoCo) | Cartesian EEF delta $(7)$ | `EVALUATION_ONLY` | Multi-task language conditioned benchmark |
| **Octo Model** | [octo-models.github.io](https://octo-models.github.io/) | Apache 2.0 | General Transformer (Cross-Embodiment) | Readout heads (Delta EEF / joints) | `PRETRAINING_ONLY` | Visual-Language-Action backbone initialization |
| **AgileX Piper Demos** (Community) | [agilexrobotics/piper_ros](https://github.com/agilexrobotics) | Apache 2.0 | Native AgileX PiPER 6-DOF | Joint positions $(q_1..q_6, \text{stroke})$ | `DIRECTLY_COMPATIBLE` | Physical fine-tuning and calibration truth |

---

## 2. In-Depth Candidate Evaluations

### 2.1 Hugging Face LeRobot Datasets
* **Source:** `https://huggingface.co/lerobot`
* **Version:** LeRobot v2.0
* **Format:** Parquet metadata + chunked observation tensors + H.264/MP4 video streams.
* **Embodiments:** Single/dual arm ALOHA, SO-100, Koch v1.1.
* **Observations:** Dual 480p RGB cameras (wrist eye-in-hand + overhead third-person), normalized motor positions.
* **Action Space:** Continuous normalized motor targets ($[-1.0, 1.0]$ or joint radians).
* **Storage Requirement:** 2 GB to 50 GB per task.
* **Compatibility Verdict:** **`CONVERTIBLE_WITH_VALIDATION`**.
  * *Integration Plan:* JARVIS-PiPER includes native LeRobot v2 export in `python/dataset/exporters.py`. Demonstrations can be loaded directly using `lerobot` PyTorch Dataset classes.

### 2.2 Open X-Embodiment (Open-X / OXE)
* **Source:** `https://github.com/google-deepmind/open_x_embodiment`
* **Format:** TensorFlow Datasets (RLDS / TFDS).
* **Embodiments:** 22 heterogeneous robot manipulators across 60+ academic institutions.
* **Observations:** RGB images (varying resolution $128\times 128$ to $640\times 480$), language task strings.
* **Action Space:** Standardized EEF delta poses: $\Delta x, \Delta y, \Delta z, \Delta \text{roll}, \Delta \text{pitch}, \Delta \text{yaw}, \text{grasp\_binary}$.
* **Storage Requirement:** > 10 TB full corpus; 5 GB per subset (e.g. `bridge_dataset`).
* **Compatibility Verdict:** **`PRETRAINING_ONLY`**.
  * *Critical Embodiment Gate:* Due to mismatched kinematics (7-DOF Franka Panda vs 6-DOF Piper arm), OXE actions cannot directly command Piper motors without inverse kinematics re-targeting. However, RGB frames provide world-class visual representations for V-JEPA pretraining.

### 2.3 ALOHA / ACT Demonstration Sets
* **Source:** Stanford Embodied AI Lab / Tony Zhao
* **Format:** Standardized HDF5 (`.hdf5`) files with `/observations/qpos`, `/observations/qvel`, `/action`.
* **Embodiments:** Dual ViperX 300 6-DOF arms.
* **Observations:** 4 camera streams (wrist left, wrist right, top, high).
* **Storage Requirement:** ~10 GB for 50 demonstration episodes.
* **Compatibility Verdict:** **`CONVERTIBLE_WITH_VALIDATION`**.
  * *Integration Plan:* Single-arm subset directly maps to PiPER's 6 revolute joints + parallel gripper $(6 + 1 = 7$ states vs ALOHA's $7 \times 2 = 14$).

### 2.4 DROID
* **Source:** `https://droid-dataset.github.io/`
* **Format:** HDF5 and Zarr.
* **Embodiments:** Franka Emika Panda in 564 everyday indoor environments.
* **Observations:** Stereo wrist RGB, external Zed RGB, language instructions.
* **Storage Requirement:** > 1.5 TB.
* **Compatibility Verdict:** **`PRETRAINING_ONLY`**.
  * *Use Case:* Visual representation pretraining of scene understanding, table surfaces, and household object geometries.

### 2.5 RoboMimic
* **Source:** `https://robomimic.github.io/`
* **Format:** HDF5 with image observations and low-dim robot states.
* **Embodiments:** Simulated Franka Panda and Sawyer manipulators in MuJoCo.
* **Compatibility Verdict:** **`EVALUATION_ONLY`**.
  * *Use Case:* Standardized algorithmic comparison between Behavior Cloning (BC), BC-RNN, and Diffusion Policy baselines.

### 2.6 Octo Foundation Model
* **Source:** `https://octo-models.github.io/`
* **License:** Apache 2.0.
* **Architecture:** ViT-Base / ViT-Small visual tokenizer with diffusion action readouts.
* **Pretrained Weights:** `octo-base` (93M params), `octo-small` (27M params).
* **Compatibility Verdict:** **`PRETRAINING_ONLY`**.
  * *Use Case:* Zero-shot visual representation backbone; requires task-specific action head fine-tuning on PiPER teleoperation demonstrations.

---

## 3. Storage Budgets & Ingestion Strategy

To ensure reproducible development without exhausting local disk storage:
1. **Never download untargeted terabyte datasets.**
2. **Download Target:** Verified 5-episode sample of LeRobot (`lerobot/pusht` or `lerobot/aloha_mobile_cabinet`) for format verification ($< 150$ MB).
3. **Execution Script:** `python scripts/download_public_dataset_sample.py` downloads a pinned, checksum-verified sample into `dataset/public/`.
