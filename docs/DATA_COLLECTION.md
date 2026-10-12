# Demonstration Data Collection Protocol & State Machine

**Protocol Version:** 2.1.0  
**Target Hardware:** AgileX PIKA Sense (Spatial Controller) + AgileX PiPER 6-DOF + Two-Finger Gripper  
**ROS 2 Bus:** ROS 2 Lyrical | Zero Frame-Drop Circular Ring Buffer  

---

## 1. Episode Lifecycle State Machine

Demonstration recording follows a strict, deterministic state machine preventing data corruption, premature truncation, or unvalidated recordings:

```
               [ IDLE ]
                  │
                  ▼ (operator starts teleop)
             [ PRECHECK ] ──► (fail: missing CAN / sensor) ──► [ REJECTED ]
                  │
                  ▼ (sensors synced & nominal)
              [ READY ]
                  │
                  ▼ (operator engages clutch / trigger)
            [ RECORDING ] ──► (e-stop / timeout) ──► [ REJECTED ]
                  │
                  ▼ (operator finishes task)
            [ FINALIZING ] (flush streaming journal)
                  │
                  ▼
            [ VALIDATING ] (7-point QA audit)
                  ├──► (QA Score >= 70 / Tier A-C) ──► [ ACCEPTED ]
                  └──► (NaN / Jerk / Jitter Fail)  ──► [ REJECTED ]
```

### State Definitions
1. **`IDLE`**: Recorder node is dormant. Ring buffers are cleared.
2. **`PRECHECK`**: Verifies topic availability (`/joint_states`, `/pika_pose`, `/camera/color/image_raw`), timestamp freshness, and disk capacity ($> 10\text{ GB}$).
3. **`READY`**: System is armed and awaiting human teleoperation input.
4. **`RECORDING`**: Multi-modal telemetry streams asynchronously into the streaming crash-proof journal (`stream_journal.jsonl`) and parallel video writer threads.
5. **`FINALIZING`**: Writing remaining buffer frames to disk; encoding MP4 videos; computing total episode duration.
6. **`VALIDATING`**: Automated 7-point QA auditor checks for timestamp monotonicity, sync jitter ($\le 2.0\text{ ms}$), joint limits, jerk continuity, and non-trivial camera frames.
7. **`ACCEPTED` / `REJECTED`**: Certified episodes are moved to `dataset/raw/`; rejected episodes are quarantined in `dataset/quarantine/` with diagnostic failure logs.

---

## 2. Step-by-Step Hardware Collection Workflow

### Step 1: Workspace & Safety Preparation
1. Clear the physical robot workstation within radius $R = 0.65\text{ m}$.
2. Verify hardware emergency stop button is within operator reach.
3. Power on 24V DC supply to PiPER base.

### Step 2: Initialize SocketCAN Interface
```bash
sudo ip link set can0 up type can bitrate 1000000
ip link show can0
```

### Step 3: Launch PIKA Sense & Teleoperation Hub
```bash
# Terminal 1: Launch PIKA Sense Vive tracker driver
bash ~/pika_ros/start_single_sensor_whit_teleop.bash

# Terminal 2: Launch JARVIS Hardware Ingestion Bus
ros2 launch jarvis_piper_bringup hardware.launch.py
```

### Step 4: Perform Interactive Episode Recording
```bash
# Start recording with natural-language task prompt
jarvis-piper record --task "Pick up red cube and place in blue tray" --operator "user_01"

# Teleoperate arm using PIKA Sense (holding clutch button)
# Press Ctrl+C or run stop command when task is complete:
jarvis-piper stop
```

### Step 5: Automated QA Audit & Export
```bash
# Verify recorded episode against 7-point quality auditor
jarvis-piper validate --dataset dataset/raw/

# Batch export to all machine learning formats
jarvis-piper export --format all
```
