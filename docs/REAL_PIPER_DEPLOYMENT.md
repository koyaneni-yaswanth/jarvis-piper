# Supervised Physical Deployment & Real Hardware Inference Guide

**Robot Hardware:** AgileX PiPER 6-DOF Manipulator with Integrated Parallel Gripper  
**Communication Bus:** SocketCAN `can0` (1 Mbps)  
**Safety Hierarchy:** `JARVIS planner -> Action Server -> Policy Adapter -> SafetySupervisor -> Controller -> Piper`  

---

## 1. Pre-Motion Safety Checklist

Before energizing motors or issuing physical motion commands:

- [ ] **Workspace Clear:** Physical perimeter ($R = 0.65\text{ m}$) free of obstacles and human bystanders.
- [ ] **Emergency Stop Test:** Physical e-stop switch tested and verified.
- [ ] **Power Supply:** Regulated 24V DC bench supply capable of 10A peak surge.
- [ ] **CAN Bus Integrity:** `can0` interface active at 1,000,000 bps with zero bus-off errors.
- [ ] **Zero Gravitational Sag:** Joints 2 and 3 supported during power-on brake release.
- [ ] **Dry Run Validation:** Policy evaluated offline with actuation disabled.

---

## 2. Dry-Run Policy Verification (Zero Physical Actuation)

Before allowing policy actions to reach robot actuators, run a dry-run test:

```bash
make policy-dry-run
```

This verifies:
1. Input observation schema matching ($16\text{D}$ state).
2. Inference latency strictly $< 20\text{ ms}$ ($50\text{ Hz}$ requirement).
3. Predicted joint targets remain inside physical limits ($[-2.618, +2.618]$, etc.).
4. Safety supervisor slew-rate filter passes all waypoints.

---

## 3. Supervised Low-Speed Physical Deployment

### Step 1: Energize Arm & Launch Controller
```bash
# Set SocketCAN baud rate
sudo ip link set can0 up type can bitrate 1000000

# Launch driver node in safe hardware mode
ros2 launch jarvis_piper_bringup hardware.launch.py --max-vel-scale 0.25
```
*Note: The `--max-vel-scale 0.25` flag clamps all actuator velocities to 25% nominal speed during initial testing.*

### Step 2: Supervised Inference Execution
```bash
# Deploy trained policy with safety supervision
jarvis-piper run --policy models/checkpoints/imitation/bc_piper_policy.pt --supervised
```

### Step 3: Executing Pick-and-Place via JARVIS
```bash
python -m jarvis_piper.cli.main execute "Pick up the red cube and place in blue tray"
```

---

## 4. Failure Recovery & Intervention Protocol

If an unexpected condition occurs during physical manipulation:
1. **Operator Emergency Stop:** Strike physical E-Stop button or press `Spacebar` in CLI.
   * The `SafetySupervisor` latches `emergency_stop_latched = True`.
   * Arm motor torques are set to zero / mechanical brakes engage.
2. **Post-Incident Recovery:**
   * Inspect scene for collisions.
   * Clear fault state via `jarvis-piper doctor`.
   * Reset supervisor via `jarvis-piper reset-safety`.
   * Return manipulator to safe home position at low speed.
