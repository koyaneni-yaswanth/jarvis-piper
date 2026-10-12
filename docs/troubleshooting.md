# JARVIS-PiPER Troubleshooting & Diagnostics Guide

This document catalogs common operational issues, diagnostic commands, and resolutions across physical hardware, simulation, and model inference.

---

## 1. Hardware & Driver Issues

### Q1: SocketCAN `can0` interface is DOWN or cannot be opened
* **Symptom:** `PiperHardwareAdapter.connect()` reports `SocketCAN interface 'can0' not found or DOWN`.
* **Root Cause:** CAN-to-USB adapter unplugged, incorrect permissions, or unconfigured bitrate.
* **Resolution:**
  ```bash
  # Check if adapter is enumerated on USB
  lsusb | grep -i -E "can|candle|agilex"
  
  # Configure and bring up can0 at 1 Mbps
  sudo ip link set can0 type can bitrate 1000000
  sudo ip link set can0 up
  
  # Verify interface state
  ip link show can0
  ```

### Q2: PIKA Sense SteamVR Lighthouse Dongle not detected
* **Symptom:** `PikaSenseAdapter.connect()` reports `SteamVR wireless receiver (VID 0x28de) not detected`.
* **Root Cause:** Udev permissions missing or receiver unplugged.
* **Resolution:**
  ```bash
  sudo cp scripts/81-vive.rules /etc/udev/rules.d/
  sudo udevadm control --reload-rules && sudo udevadm trigger
  ```
  Unplug and reconnect the SteamVR wireless dongle.

---

## 2. Multi-Modal Synchronization & Recording

### Q3: High Jitter Warning ($\sigma > 2.0\text{ ms}$) during recording
* **Symptom:** Quality auditor flags `FAIL_SYNC_JITTER` on recorded episodes.
* **Root Cause:** Heavy background CPU load or disk I/O contention during video encoding.
* **Resolution:**
  * Ensure video frames are enqueued to the asynchronous thread rather than encoded in the main ROS 2 callback thread.
  * Reduce image resolution to 480p ($640\times 480$) or 240p ($320\times 240$) for multi-camera setups.

---

## 3. Dataset Export & Downstream Training

### Q4: HDF5 Export fails with `ModuleNotFoundError: No module named 'h5py'`
* **Symptom:** Exporter falls back to compressed `.npz` files instead of native `.hdf5`.
* **Resolution:**
  ```bash
  pip install h5py
  jarvis-piper export --format aloha
  ```

---

## 4. Policy Inference & Safety Interlocks

### Q5: Policy commands rejected with `Cartesian workspace violation`
* **Symptom:** `SafetySupervisor.filter_and_validate_action()` returns `is_safe = False`.
* **Root Cause:** Neural network policy output predicted a waypoint outside the defined manipulation bounding box:
  * $x \in [0.10, 0.60]\text{ m}$
  * $y \in [-0.45, 0.45]\text{ m}$
  * $z \in [0.015, 0.55]\text{ m}$
* **Resolution:** Inspect policy normalization parameters (`obs_mean`, `obs_std`) in `models/checkpoints/imitation/bc_piper_policy.pt`. Ensure training data was clipped to the physical table bounds.
