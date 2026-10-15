# JARVIS-PiPER: Current Engineering State

**Last Updated:** October 15, 2026  
**Host Target:** `humble-NUC14RVS-B` (Ubuntu 22.04.5 LTS / ROS 2 Humble)  
**Repository Branch:** `main` (commit `fecfb4a`)  
**Active Safety Mode:** `MOCK` / `HARDWARE_READ_ONLY`

---

## 1. System Summary

JARVIS-PiPER is a language-conditioned embodied AI manipulation pipeline for the 6-DOF AgileX PiPER robot arm, integrating multimodal observation (RealSense D405 wrist camera, DECXIN overhead camera), PIKA Sense 6-DOF optical tracking (SteamVR/HTC Vive Lighthouse), and imitation learning policies (Behavior Cloning, Action Chunking, and V-JEPA visual representations).

All automated test suites execute locally on the NUC host within `.venv` (Python 3.10.12 with PyTorch 2.14.1+cu130 linked and ROS 2 Humble bindings), with **163 / 163 passing tests**.

---

## 2. Component Implementation Status

| Component | Architecture Role | Operational Mode | Evidence / Verification |
| :--- | :--- | :--- | :--- |
| **Safety Supervisor** | Independent action validation gateway | Enforced on all actions | Clamping limits $[-2.618, 2.618]$ rad, velocity $\le 1.5$ rad/s, workspace bounding box $X \in [0.05, 0.65], Y \in [-0.45, 0.45], Z \in [0.02, 0.65]$ m. NaN rejection verified. |
| **Dataset Pipeline** | MCAP/HDF5 parsing, validation & conversion | Active | Verified 20 real demonstration MCAPs (2.1 GB); transcoded 5 episodes (2,274 physical frames) into HDF5 via `tools/dataset_convert.py`. |
| **Imitation Learning** | Behavior Cloning & Action Chunking (ACT) | CPU PyTorch | Trained & evaluated both BC (MSE: 0.1386) and ACT (MSE: 0.0702, -49.3% error) on physical demonstrations. Checkpoints saved. |
| **Task Orchestration** | Intent parsing & Pick-and-place FSM | Structured allowlist | Preconditions, timeouts, and operator-gated hardware dispatch verified end-to-end. |
| **Sensor Adapters** | RealSense D405, DECXIN, PIKA Sense | Read-only / Mock | Multi-adapter dependency injection implemented; hardware nodes passively audited on USB/CAN buses. |
| **Robot Gateway** | PiPER CAN bus command dispatch | Hardware Verified | `can0` active at 1 Mbps; live 200 Hz telemetry and physical motion verified via low-risk supervised Z nudge. |

---

## 3. Verification & Deployment Status

1. **Automated Test Suite:** 163 passed, 2 skipped, 0 failed in 8.14s (`bash scripts/run_nuc_tests.sh`).
2. **Physical Motion Authorization & Execution:** Physical motion verified under operator authorization. Protocol `PHYSICAL-TEST-001-SUPERVISED-NUDGE` executed successfully: +30 mm Z nudge completed, encoder position verified, returned to start, and motors cleanly disarmed.
3. **Current Hardware State:** `can0` UP; motors currently disarmed (`[False, False, False, False, False, False]`) in standby.
4. **Batch Scaling (Optional):** Remaining MCAP episodes (episodes 2, 6–19) can be transcoded via `python3 tools/dataset_convert.py /home/humble/pika_mgat_files/episodes/ -o /home/humble/pika_mgat_files/hdf5/` as needed for expanded multi-task training.

