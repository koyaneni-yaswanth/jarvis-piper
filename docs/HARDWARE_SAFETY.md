# JARVIS-PiPER: Hardware Safety Constitution & Perception Isolation

**Document Version:** 2.0.0  
**Effective Date:** 2026-10-15  
**Compliance Standard:** Mandatory for all simulation, teleoperation, and physical execution  

---

## 1. Foundational Safety Axioms

1. **VLM Perception is Strictly Untrusted:**  
   Natural language models, captioning models, and vision-language foundation models (BLIP, CLIP, LLaVA) are stochastic perception estimators. Their outputs—including generated text, candidate rankings, and proposed bounding boxes—shall **never** be passed directly to robot joint controllers or motor actuators.

2. **Perception-Actuation Air Gap:**  
   The system enforces a unidirectional architecture:
   ```
   [Camera Stream] ──> [VLM Perception] ──> [Task Planner (Hypothesis)]
                                                      │
                                                      ▼
                                            [Safety Supervisor]
                                            (Independent Gate)
                                                      │
                                      ┌───────────────┴───────────────┐
                                      ▼                               ▼
                              [Rejected / Logged]             [Hardware Actuator]
                                                        (Requires Operator Token)
   ```

3. **Default Zero-Motion Policy:**  
   - All modules, adapters, launch scripts, and CLI entry points default to `MOCK` mode or `dry_run=True`.
   - Motor actuation requires explicit human confirmation via authorization token (`ENABLE MOTION`).
   - Any unhandled exception, tracking loss, or communication timeout immediately triggers a controlled halt.

---

## 2. SafetySupervisor Verification & Interlocks

The `SafetySupervisor` ([`jarvis/safety.py`](file:///d:/yaswanth/ranger%20mini/jarvis-piper/jarvis/safety.py)) acts as the sole authoritative arbiter of physical motion commands:

### 2.1 Workspace Geofencing
Every end-effector coordinate $(x, y, z)$ proposed by perception or teleoperation is validated against fixed kinematic boundaries:
- **X (Forward reach):** $+0.10\text{ m} \le x \le +0.60\text{ m}$
- **Y (Lateral reach):** $-0.45\text{ m} \le y \le +0.45\text{ m}$
- **Z (Vertical altitude):** $+0.015\text{ m} \le z \le +0.55\text{ m}$ (table collision avoidance enforced at $z = 0.015\text{ m}$)

### 2.2 Joint Limit Guardrails (AgileX PiPER 6-DOF)
- **Joint Position Limits:** Strictly enforced in software to prevent mechanical collision with internal hard stops.
- **Joint Velocity Clamping:** Maximum angular velocity capped at $1.5\text{ rad/s}$ ($86^\circ/\text{s}$) across all 6 axes.
- **Maximum Step Delta:** Maximum per-tick displacement constrained to $\Delta q_{max} = 0.05\text{ rad}$ at $50\text{ Hz}$.

### 2.3 Operator Hardware Gates
When a user submits a natural-language task such as `"Pick up the red cube"`:
1. The planner generates a 19-step inspectable `TaskPlan`.
2. Perception steps (1–10) acquire images, assess scene context, and compute candidates.
3. Steps 11–18 are explicitly flagged `requires_hardware=True` and `requires_operator_confirmation=True`.
4. If executed without `operator_authorized=True`, execution halts cleanly with status `AWAITING_OPERATOR`. No CAN packets are transmitted.

---

## 3. Communication & Tracking Timeouts

- **PIKA 6-DOF Optical Tracking Age:** $\le 0.100\text{ s}$ (100 ms). If tracking age exceeds 100 ms or the deadman clutch is disengaged, target position freezes instantly.
- **CAN Bus Health:** CAN frames monitored for transmit/receive errors; stale joint feedback ($> 50\text{ ms}$) triggers an emergency stop.
- **Physical E-Stop:** Hardware emergency stop switch must be physically wired and accessible at all times during powered testing.
