# JARVIS-PiPER Known Issues & Risk Register

**Status:** Living Engineering Document  

---

## 1. Active Issues & Technical Traps

### ISSUE-01: Conda Python 3.14.7 Collision with ROS 2 Humble
- **Severity:** High
- **Description:** On the target NUC machine, Conda is installed under `/home/humble/miniconda3` with Python 3.14.7. If Conda environment is active, launching ROS 2 nodes fails with binary symbol mismatch (`Expected 96 from C header, got 88 from PyObject` / `ImportError: cannot import name 'rclpy'`).
- **Workaround / Fix:** Strictly deactivate Conda (`conda deactivate`) and ensure `/usr/bin/python3` (Python 3.10.12) is the active interpreter before sourcing `/opt/ros/humble/setup.bash`.

---

### ISSUE-02: PiPER Joint 3 (Elbow Pitch) Mechanical Coordinate Limit
- **Severity:** Medium
- **Description:** Joint 3 coordinate boundaries are strictly $[-2.967, 0.000]\,\text{rad}$ ($[-170^\circ, 0^\circ]$). Any positive joint command ($q_3 > 0$) causes physical self-collision between arm links.
- **Workaround / Fix:** Enforced inside `jarvis.safety.SafetySupervisor` and `jarvis.kinematics`. Unit tests and trajectory generators strictly initialize Joint 3 with negative angles (nominal: $-0.60\,\text{rad}$).

---

### ISSUE-03: SocketCAN `can0` Interface Down / Unattached
- **Severity:** Medium (Hardware Blocking)
- **Description:** If the USB-to-CAN adapter is unplugged or the interface is not brought up, attempting to communicate with the real arm raises `CanInterfaceDownError`.
- **Workaround / Fix:** Bring up interface with:
  ```bash
  sudo ip link set can0 up type can bitrate 1000000
  ```
  In software, `RealPiperArm` gracefully catches missing interfaces and `jarvis doctor` reports clear remediation hints.

---

### ISSUE-04: SteamVR Wireless Dongle Missing udev Permissions
- **Severity:** Medium (Hardware Blocking)
- **Description:** Non-root users cannot read optical packets from the SteamVR wireless dongle (VID `0x28de`, PID `0x2101`) without proper udev rules.
- **Workaround / Fix:** Install non-destructive rule:
  ```bash
  echo 'SUBSYSTEM=="usb", ATTRS{idVendor}=="28de", MODE="0666", GROUP="plugdev"' | sudo tee /etc/udev/rules.d/99-pika-sense.rules
  sudo udevadm control --reload-rules && sudo udevadm trigger
  ```

---

### ISSUE-05: Vendor Launch File Defaulting to `auto_enable=true`
- **Severity:** Critical Safety Hazard
- **Description:** `~/piper_ros/src/piper/launch/start_single_piper.launch.py` declares argument `auto_enable=true`. If launched directly, the robot may energize and jump into a default pose without operator authorization.
- **Workaround / Fix:** Never invoke vendor launch files directly. All actuation must route through `jarvis.cli teleop --execute` with explicit token `"ENABLE MOTION"`.

---

### ISSUE-06: Milestone 2 Strict Read-Only Actuation Lock
- **Severity:** Informational Safety Policy
- **Description:** In Milestone 2, physical motor actuation is locked in software (`milestone_lock = True` and `RealPiperArm.send_joint_command()` raises `MotionNotAuthorizedError`). Physical actuation is only unlocked in Milestone 17 physical commissioning.
- **Workaround / Fix:** Use `MockArm` or `SIMULATION` / `MOCK` mode for testing control loops; real arm interface is strictly read-only for verifying feedback reception and encoder packet decoding.
