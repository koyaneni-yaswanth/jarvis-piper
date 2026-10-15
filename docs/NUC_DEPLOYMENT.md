# JARVIS-PiPER: Intel NUC 14 Deployment & Operational Runbook

**Target Machine:** Intel NUC 14 (`humble-NUC14RVS-B`)  
**Operating System:** Ubuntu 22.04.5 LTS  
**ROS 2 Distro:** Humble Hawksbill  
**System Python:** `/usr/bin/python3` (Python 3.10.12)  
**Canonical Path:** `~/robotics/jarvis-piper`  

---

## 1. Repository Synchronization & Directory Recovery

### 1.1 Preserve Diagnostic Scripts from Nested Clone
If a nested clone exists at `~/robotics/jarvis-piper/jarvis-piper`:
```bash
cd ~/robotics/jarvis-piper

# 1. Ensure target tools directory exists
mkdir -p tools/diagnostics

# 2. Safely copy the 3 unique diagnostic scripts from the inner clone
if [ -d "jarvis-piper/scripts" ]; then
    cp -n jarvis-piper/scripts/check_piper_feedback.py tools/diagnostics/ 2>/dev/null || true
    cp -n jarvis-piper/scripts/inspect_piper_feedback.py tools/diagnostics/ 2>/dev/null || true
    cp -n jarvis-piper/scripts/monitor_piper_joints.py tools/diagnostics/ 2>/dev/null || true
fi

# 3. Verify files were preserved
ls -la tools/diagnostics/

# 4. Safely remove the nested clone without touching parent .git
rm -rf jarvis-piper
```

### 1.2 Pull the Latest Version
```bash
cd ~/robotics/jarvis-piper
git fetch origin
git checkout main
git pull origin main
```

---

## 2. Python Environment Setup

Do **not** use `sudo pip`. Always use a virtual environment:

```bash
cd ~/robotics/jarvis-piper

# 1. Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 2. Upgrade pip and build tooling
pip install --upgrade pip setuptools wheel

# 3. Install JARVIS-PiPER in editable mode with development dependencies
pip install -e ".[dev]"

# 4. Verify CLI entry points
jarvis --help
jarvis-piper --help
```

---

## 3. VLM Offline Model Pre-Caching

Because the physical robot workcell may be run on an isolated subnet without WAN access, pre-cache model weights in advance:

```bash
source ~/robotics/jarvis-piper/.venv/bin/activate
pip install transformers pillow torch torchvision accelerate

# 1. Pre-cache CLIP ViT-B/32 (~338 MB)
python -c "
from transformers import CLIPModel, CLIPProcessor
CLIPModel.from_pretrained('openai/clip-vit-base-patch32')
CLIPProcessor.from_pretrained('openai/clip-vit-base-patch32')
print('[OK] CLIP model cached successfully.')
"

# 2. Pre-cache BLIP Base (~990 MB)
python -c "
from transformers import BlipForConditionalGeneration, BlipProcessor
BlipProcessor.from_pretrained('Salesforce/blip-image-captioning-base')
BlipForConditionalGeneration.from_pretrained('Salesforce/blip-image-captioning-base')
print('[OK] BLIP model cached successfully.')
"
```

---

## 4. Hardware Verification & Passive Diagnostics

### 4.1 Passive CAN Bus Inspection (AgileX PiPER)
Verify SocketCAN interface `can0` without enabling motors:
```bash
# Bring up CAN interface at 1,000,000 baud
sudo ip link set can0 type can bitrate 1000000
sudo ip link set can0 up

# Verify interface state
ip -details link show can0

# Listen passively for joint telemetry broadcast (Ctrl+C to exit)
candump can0
```

### 4.2 Camera Device Enumeration
```bash
# Verify USB cameras
v4l2-ctl --list-devices

# Verify Intel RealSense D405
rs-enumerate-devices -s
```

### 4.3 Run JARVIS System Doctor
```bash
source ~/robotics/jarvis-piper/.venv/bin/activate
jarvis doctor
jarvis vlm --evaluate
```

---

## 5. ROS 2 Workspace Build & Interface Generation

```bash
cd ~/robotics/jarvis-piper/ros2_ws
source /opt/ros/humble/setup.bash

# 1. Update and install workspace dependencies via rosdep
sudo rosdep init || true
rosdep update
rosdep install --from-paths src --ignore-src -r -y --rosdistro humble

# 2. Build ROS 2 interfaces and nodes
colcon build --symlink-install --cmake-args -DCMAKE_BUILD_TYPE=Release

# 3. Source and verify generated messages
source install/setup.bash
ros2 interface list | grep jarvis_piper
```

---

## 6. Safe System Bringup (Zero-Hardware Verification)

Verify full bringup in `MOCK` mode before any live hardware testing:
```bash
# 1. Validate full pytest suite
pytest tests/ -v

# 2. Run mock VLM task planner
jarvis vlm --task "Describe the scene" --vlm-type mock --cam-type mock

# 3. Verify manipulation safety gate (must block at Step 12 without moving arm)
jarvis vlm --task "Pick up the red cube" --vlm-type mock --cam-type mock
```
