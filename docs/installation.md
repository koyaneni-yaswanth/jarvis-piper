# JARVIS-PiPER Installation Guide

This guide covers setup and installation across Linux workstations, WSL2 (Ubuntu 24.04 / 26.04), and Docker environments.

---

## 1. System Requirements

- **Operating System**: Ubuntu 24.04 LTS (Noble) or Ubuntu 26.04 LTS (Lyrical), native or under WSL2.
- **Python**: Python 3.10+ (Tested up to Python 3.14).
- **ROS 2**: ROS 2 Jazzy or ROS 2 Lyrical (optional; pure Python and Mock modes do not require ROS 2).
- **Storage**: Minimum 50 GB free disk space recommended for multi-modal demonstration datasets.
- **GPU (Optional)**: NVIDIA GPU with CUDA 12+ for V-JEPA pretraining acceleration.

---

## 2. Quickstart Installation (Automated)

Clone the repository and run the automated installer:

```bash
git clone https://github.com/recvn/jarvis-piper.git
cd jarvis-piper

# Run automated setup
./scripts/install.sh
```

The script will:
1. Verify system prerequisites.
2. Install Python package dependencies in editable development mode (`pip install -e .`).
3. Generate runtime dataset and model output directories.
4. Create `configs/local.yaml` from template.

---

## 3. Environment Configuration

Source the environment setup script before launching workflows:

```bash
source scripts/setup.sh
```

This exports `PYTHONPATH`, configures `ROS_DOMAIN_ID=10`, sets the DDS RMW implementation (`rmw_cyclonedds_cpp`), and sources ROS 2 workspaces if present.

---

## 4. Building the ROS 2 Workspace (Optional)

If developing ROS 2 nodes or building custom message interfaces:

```bash
# Source ROS 2 Lyrical
source /opt/ros/lyrical/setup.bash

# Build all packages with symlink install
./scripts/build.sh
```

---

## 5. Verification: Running the System Doctor

Verify that all dependencies and adapters are operating properly:

```bash
jarvis-piper doctor
```

Example verified output:
```text
================================================================================
                    JARVIS-PiPER SYSTEM & HARDWARE CHECK
================================================================================
 Host Platform            Linux (x86_64)                         PASS
 Python Environment       3.14.4                                 PASS
 ROS 2 Distro             Lyrical (Ubuntu 26.04)                 PASS
 GPU Accelerator          NVIDIA GeForce RTX 5060                PASS
 Free Storage             946.78 GB                              PASS
 PiPER HAL Adapter        Loaded                                 PASS
 PIKA Sense Adapter       Loaded                                 PASS
 PIKA Gripper Adapter     Loaded                                 PASS
================================================================================
```

---

## 6. Zero-Hardware End-to-End Demo

Run the end-to-end synthetic demo to verify data logging, export, and model training:

```bash
./scripts/demo.sh
```
