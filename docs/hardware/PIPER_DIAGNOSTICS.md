# AgileX PiPER Arm: Non-Destructive Passive Diagnostics Runbook

This runbook guides operators through diagnosing the PiPER manipulator's electrical, bus, and feedback readiness on the physical host without altering system state or commanding motion.

---

## 1. Automated Passive Diagnostic Script

Execute the bundled read-only diagnostics script:
```bash
./scripts/diagnose_piper.sh can0
```

This script performs 5 sequential non-destructive audits:
1. **Kernel SocketCAN Modules**: Checks for `can`, `can_raw`, `can_dev`, `gs_usb`.
2. **USB-to-CAN Enumeration**: Checks for USB vendor/product IDs (`0483:5740`, `1d50:606f`, `gs_usb`).
3. **SocketCAN Interface State**: Audits link state, bitrate (`1000000`), queue length, and error counters.
4. **Vendor Workspace Safety Inspection**: Verifies whether `~/piper_ros` contains dangerous `auto_enable:=true` defaults.
5. **Passive Sniffing**: Performs a bounded 2-second telemetry capture (`candump`) with zero packets transmitted.

---

## 2. Step-by-Step Manual Diagnosis

### Step 1: Verify Hardware USB Connection
```bash
lsusb | grep -iE "can|candle|gs_usb|stm32|0483:5740|1d50:606f"
```
* **PASS**: Adapter is enumerated on the USB tree.
* **FAIL**: No matching devices found. Check USB cable and port seating.

### Step 2: Check Kernel dmesg Log for Device Attachment
```bash
dmesg | grep -iE "can|gs_usb" | tail -n 20
```
Look for:
```text
gs_usb 1-1:1.0: Configuring for 1 interfaces
gs_usb 1-1:1.0: Device registered as can0
```

### Step 3: Inspect Network Interface Link Status
```bash
ip -s -d link show can0
```
Inspect the `can state`:
* `ERROR-ACTIVE`: Normal operating state. Transmission and reception counters are within healthy limits.
* `ERROR-WARNING` / `ERROR-PASSIVE`: High error frame count detected on the physical bus. Check termination resistors.
* `BUS-OFF`: Fatal CAN bus error. Interface entered protective shutdown. Recover with:
  ```bash
  sudo ip link set can0 down
  sudo ip link set can0 up type can bitrate 1000000
  ```

### Step 4: Passive Telemetry Frame Capture
```bash
timeout 2s candump can0
```
Look for feedback frames in the ID range `0x2A1` - `0x2A6`:
```text
can0  2A1   [8]  00 00 00 00 00 00 00 00
can0  2A2   [8]  10 27 00 00 00 00 00 00
can0  2A3   [8]  F0 D8 FF FF 00 00 00 00
can0  2A4   [8]  00 00 00 00 00 00 00 00
can0  2A5   [8]  A0 0F 00 00 00 00 00 00
can0  2A6   [8]  00 00 00 00 00 00 00 00
```
If frames appear, the microcontroller feedback loop is fully active and the arm is communicating healthily.

---

## 3. Python Driver Passive Feedback Verification

To verify that the application layer decodes feedback correctly without commanding motion:

```bash
python -c "
from jarvis.hardware import RealPiperArm
arm = RealPiperArm(can_channel='can0')
arm.connect()
state = arm.get_joint_state()
print('Joint Positions (rad):', state)
print('Feedback Freshness (s):', arm.get_feedback_freshness())
arm.disconnect()
"
```
* If `can0` is missing or down, raises `CanInterfaceDownError` with exact remedy.
* If physical arm is disconnected, feedback freshness will exceed 100 ms timeout and raise `StaleFeedbackError`.
* If any joint frame contains invalid count or corrupted bits, raises `InvalidJointStateError`.
