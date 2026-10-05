# Troubleshooting & Diagnostics

This document outlines solutions to common hardware, networking, ROS 2, and environment issues.

---

## 1. Quick Diagnostics

Always begin by running the system doctor:

```bash
jarvis-piper doctor
```

---

## 2. Common Issues & Solutions

### A. CAN-bus Interface (`can0`) Down or Not Detected
- **Symptom**: PiPER arm does not respond; `check_hardware.sh` reports no CAN device.
- **Solution**:
  1. Verify USB-to-CAN adapter is plugged in: `lsusb`
  2. Bring up interface:
     ```bash
     sudo ip link set can0 type can bitrate 1000000
     sudo ip link set can0 up
     ```
  3. Verify CAN traffic: `candump can0`

### B. ROS 2 Domain ID Conflicts
- **Symptom**: Multiple machines on the local network interfere with topic streams.
- **Solution**:
  1. Ensure `export ROS_DOMAIN_ID=10` is set in all terminals (or run `source scripts/setup.sh`).
  2. Ensure DDS discovery multicast is permitted on the firewall.

### C. Camera Topic Disconnections or Frame Drops
- **Symptom**: Wrist camera FPS drops below 30 or fails to open.
- **Solution**:
  1. Verify camera permissions: `sudo chmod 666 /dev/video*`
  2. Check USB 3.0 bandwidth contention: connect arm CAN adapter and camera to separate USB root hubs.

### D. Colcon Build Fails with Python Setuptools Warnings
- **Symptom**: Warning regarding deprecated `tests_require` on Python 3.14.
- **Solution**: JARVIS-PiPER packages use modern `ament_python` specifications without deprecated setuptools keys. Clean existing cache:
  ```bash
  ./scripts/clean.sh && ./scripts/build.sh
  ```

### E. PyTorch Not Installed in Minimal Environments
- **Symptom**: `train_vjepa` or `evaluate_vjepa` reports PyTorch missing.
- **Solution**: JARVIS-PiPER automatically falls back to simulated smoke tests so workflows do not crash. To run GPU training, install PyTorch into your virtual environment:
  ```bash
  pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
  ```
