# JARVIS-PiPER Safety Manual & Operational Constraints

**Safety Classification:** Level 2 Supervised Collaborative Manipulation  
**Emergency Stop Response:** $< 10\text{ ms}$ software latch, physical hard-stop  

---

## 1. Safety Principles & Zero-Tolerance Constraints

1. **Explicit Operator Authorization:** The physical robot must never actuate autonomously without explicit operator confirmation.
2. **Never Bypass the Safety Supervisor:** All policy predictions, teleoperation streams, and scripted motions must flow through the `SafetySupervisor`.
3. **Dead-Man Clutch Interlock:** In teleoperation mode, human operator must maintain continuous grip pressure on the PIKA Sense clutch. Releasing the clutch immediately zeros target velocities.
4. **Collision Bounding Box:** The robot tool flange and fingertips must remain strictly inside the defined Cartesian workspace:
   * Forward Reach: $0.10\text{ m} \le x \le 0.60\text{ m}$
   * Lateral Span: $-0.45\text{ m} \le y \le 0.45\text{ m}$
   * Vertical Clearance: $0.015\text{ m} \le z \le 0.55\text{ m}$

---

## 2. Hard Kinematic & Dynamic Limits

| Axis | Position Limits (rad) | Velocity Limit ($\text{rad/s}$) | Acceleration Limit ($\text{rad/s}^2$) | Max Effort ($\text{N}\cdot\text{m}$) |
|:---|:---|:---|:---|:---|
| **Joint 1** | $[-2.618, +2.618]$ | $1.5$ (Capped from $5.0$) | $3.0$ | $100.0$ |
| **Joint 2** | $[0.000, +3.142]$ | $1.5$ (Capped from $5.0$) | $3.0$ | $100.0$ |
| **Joint 3** | $[-2.967, 0.000]$ | $1.5$ (Capped from $5.0$) | $3.0$ | $100.0$ |
| **Joint 4** | $[-1.745, +1.745]$ | $1.5$ (Capped from $5.0$) | $3.0$ | $100.0$ |
| **Joint 5** | $[-1.220, +1.220]$ | $1.5$ (Capped from $5.0$) | $3.0$ | $100.0$ |
| **Joint 6** | $[-2.094, +2.094]$ | $1.5$ (Capped from $3.0$) | $3.0$ | $100.0$ |
| **Gripper** | $[0.000, 0.035]\text{ m}$ | $0.5\text{ m/s}$ | $2.0\text{ m/s}^2$ | $10.0\text{ N}$ |

---

## 3. Emergency Stop (E-Stop) Procedures

* **Software Trigger:** Press `Spacebar` in any active terminal or call `SafetySupervisor.trigger_estop()`.
* **Hardware Trigger:** Strike the physical red mushroom E-Stop button wired in series with the 24V power line.
* **Latch Mechanism:** Once triggered, the software state transitions to `ESTOP` and rejects all motion commands until explicitly cleared with `reset_estop()`.
