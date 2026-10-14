# PIKA Sense & Base Stations: Hardware Setup & Integration

This document specifies the physical setup, base station placement, USB receiver dongle configuration, and user permissions required for the PIKA Sense teleoperation device.

---

## 1. Hardware Overview

The PIKA teleoperation system consists of:
1. **PIKA Sense**: Handheld tracking device equipped with photodiodes for infrared sweep sensing, dead-man clutch button, and trigger/slider controls.
2. **PIKA Stations (Lighthouse Base Stations)**: Two SteamVR / HTC Vive compatible infrared laser emitters providing structured spatial illumination.
3. **SteamVR Wireless Dongle**: USB receiver (Vendor ID `0x28de`, e.g. SteamVR Watchman Dongle) providing RF communication between PIKA Sense and the host computer.

---

## 2. Base Station Placement & Geometry

To achieve sub-millimeter tracking accuracy and prevent optical occlusion:
- **Quantity**: 2 Base Stations (Station A and Station B).
- **Height**: Mounted at $2.0\,\text{m} - 2.5\,\text{m}$ above the floor, angled downward at $30^\circ - 45^\circ$ toward the center of the teleoperation volume.
- **Distance**: Located opposite each other, approximately $3.0\,\text{m} - 4.5\,\text{m}$ apart diagonally across the workspace.
- **Line of Sight**: Both base stations must have uninhibited line-of-sight to the PiPER arm and the operator hand volume.
- **Stability**: Base stations contain high-speed spinning optical rotors. Mount on rigid wall brackets or weighted tripods. Vibrating mounts cause immediate tracking jitter and rejectable pose estimation.
- **Sync Mode**: Ensure Base Stations are configured on distinct channels (e.g. Channel 1 and Channel 2, or Mode 'b' and Mode 'c').

---

## 3. USB Dongle Connection & Permissions

1. **Connect Dongle**:
   - Plug the SteamVR wireless USB dongle into a USB 2.0 or USB 3.0 port on the target machine.
   - For optimal wireless RF performance, keep the dongle at least 30 cm away from high-power Wi-Fi antennas or USB 3.0 hubs with RF leakage.

2. **Verify Enumeration**:
   ```bash
   lsusb | grep -iE "28de:|valve|steam|htc"
   ```
   Expected device output:
   ```text
   Bus 001 Device 005: ID 28de:2000 Valve Software Steam Controller
   # OR
   Bus 001 Device 006: ID 28de:2101 Valve Software Wireless Receiver
   ```

3. **User Group Permissions**:
   The user must belong to the `dialout` and `plugdev` groups to access serial and raw USB endpoints:
   ```bash
   sudo usermod -aG dialout $USER
   sudo usermod -aG plugdev $USER
   ```
   *Note: Group membership changes require logging out and logging back in.*

4. **Non-Destructive udev Rules**:
   Apply non-destructive udev rules to grant read/write access without removing existing rules:
   ```bash
   sudo tee /etc/udev/rules.d/60-pika-steamvr.rules << 'EOF'
   # SteamVR / Vive USB Wireless Receiver
   KERNEL=="hidraw*", ATTRS{idVendor}=="28de", MODE="0666"
   SUBSYSTEM=="usb", ATTRS{idVendor}=="28de", MODE="0666", GROUP="plugdev"
   SUBSYSTEM=="tty", ATTRS{idVendor}=="28de", MODE="0666", GROUP="dialout"
   EOF

   sudo udevadm control --reload-rules
   sudo udevadm trigger
   ```

---

## 4. Passive Verification

Run the bundled passive diagnostic script:
```bash
./scripts/diagnose_pika.sh
```
Verify that all 5 checks return `[PASS]`.
