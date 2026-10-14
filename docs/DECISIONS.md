# JARVIS-PiPER Architecture Decision Records (ADR)

**Status:** Living Engineering Log  

---

### ADR-001: Central Safety Supervisor as Sole Hardware Gateway
* **Context:** The system incorporates multiple sources of action commands: human teleoperation via PIKA Sense, language model task planners, imitation learning policies (BC, ACT), and simulated trajectory replays. If any component could independently send CAN packets to the PiPER arm, safety invariants could be bypassed.
* **Decision:** All hardware communication is strictly gated behind `jarvis.safety.SafetySupervisor`. No adapter may actuate motors without an explicit `ALLOW` decision from the supervisor.
* **Consequences:** Eliminates accidental motor motion. Enforces unified E-stop, tracking watchdog, and bounding box validation across all execution pathways.

---

### ADR-002: System Python 3.10 Mandatory for ROS 2 Humble Runtime
* **Context:** The target NUC has Conda installed under `/home/humble/miniconda3` with Python 3.14.7. Attempting to run ROS 2 Humble nodes under Conda fails due to binary C-extension incompatibilities (`Expected 96 from C header, got 88 from PyObject`). System Python 3.10 (`/usr/bin/python3`) imports `rclpy` cleanly.
* **Decision:** Enforce system Python 3.10 as the designated runtime for all ROS 2 nodes, hardware drivers, and real-time telemetry. Non-ROS machine learning components requiring newer PyTorch builds must be isolated in a dedicated virtual environment or communicate via documented message interfaces.
* **Consequences:** Prevents segmentation faults and DLL/so symbol mismatches. Ensures 100% stability with ROS 2 Humble C-libraries.

---

### ADR-003: Single Manipulator Priority for Initial Physical Deployment
* **Context:** Although the platform architecture supports multi-arm topologies (e.g. Dual-PiPER or PiPER + Nero), only ONE PiPER arm is currently physically mounted and wired to `can0`.
* **Decision:** Focus the immediate real-hardware milestone strictly on the single AgileX PiPER 6-DOF arm. Retain modular multi-arm class interfaces (`MultiArmSupervisor`), but flag multi-arm hardware tests as `BLOCKED_HARDWARE` until additional physical arms are energized.
* **Consequences:** Prevents diffusion of effort; delivers a reliable, robust baseline before scaling to bimanual coordination.

---

### ADR-004: Deterministic Behavioral Cloning Baseline Before ACT & V-JEPA
* **Context:** Complex policies such as Action Chunking with Transformers (ACT) and visual foundation models (V-JEPA 2) introduce substantial compute overhead, large dependency trees, and non-trivial hyperparameter tuning.
* **Decision:** Build and empirically verify a lightweight, deterministic Multi-Layer Perceptron (MLP) Behavioral Cloning baseline first. Use this baseline to validate data collection, normalization, checkpointing, and safe rollout before scaffolding advanced research models.
* **Consequences:** Fast training iterations on CPU/entry-level GPUs; guarantees an end-to-end working baseline within minutes.

---

### ADR-005: Non-Destructive Passive Diagnostics
* **Context:** Vendor scripts in `~/pika_ros` and `~/piper_ros` contained dangerous operations (e.g., deleting `/etc/udev/rules.d/` files and launching with `auto_enable=true`).
* **Decision:** Diagnostics and installation scripts must be strictly non-destructive. They must audit device presence and file state without resetting git branches, deleting directories, or altering existing system configurations without explicit approval.
* **Consequences:** Preserves existing user work, driver packages, and calibration artifacts intact.

---

### ADR-006: Atomic Append-Only Journaling for Teleoperation Data Collection
* **Context:** Demonstrations recorded on physical hardware can be lost or corrupted if the host PC freezes, the battery drops, or the operator terminates the process abruptly.
* **Decision:** Every recorded timestep is written immediately to an append-only JSONL journal (`stream_journal.jsonl`) flushed to disk upon write. Summary metadata is compiled only upon clean episode finalization.
* **Consequences:** Zero recorded frames are lost in the event of an unexpected process termination.
