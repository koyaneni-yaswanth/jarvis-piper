# JARVIS-PiPER: Simulation vs. Physical Trajectory Report

**Dataset Episode:** `session`  
**Dataset Schema:** `DIRECT_JOINT_TELEMETRY`  
**Evaluated Steps:** 46 / 46  
**Evaluation Timestamp:** 2026-10-16T17:46:33Z  
**Overall Status:** **PASS** (Fidelity Score: **74.6 / 100**)

---

## 1. Executive Summary

The simulation-to-real validation engine executed forward physics playback in MuJoCo 3.16.0 using the exact physical recording baseline.

| Evaluation Metric | Measured Value | Standard Threshold | Status |
| :--- | :--- | :--- | :---: |
| **Cartesian TCP MAE** | **11.27 mm** | $< 25.0\,\text{mm}$ | **PASS** |
| **Cartesian TCP RMSE** | **11.43 mm** | $< 35.0\,\text{mm}$ | **PASS** |
| **Cartesian TCP Max Error** | **13.17 mm** | $< 50.0\,\text{mm}$ | **PASS** |
| **Overall Joint MAE** | **0.93°** | $< 5.0^\circ$ | **PASS** |
| **Overall Joint MSE** | **0.000555 rad²** | $< 0.01\,\text{rad}^2$ | **PASS** |
| **Gripper Stroke MAE** | **0.04 mm** | $< 5.0\,\text{mm}$ | **PASS** |

---

## 2. Per-Joint Tracking Fidelity

| Kinematic DOF | Tracking MAE (deg) | Peak Error (deg) | Pearson Correlation ($r$) |
| :--- | :---: | :---: | :---: |
| Joint 1 | 0.00° | 0.00° | 1.0000 |
| Joint 2 | 2.09° | 2.21° | 0.0000 |
| Joint 3 | 2.04° | 2.22° | 0.0000 |
| Joint 4 | 0.00° | 0.00° | 1.0000 |
| Joint 5 | 1.44° | 1.61° | 0.0000 |
| Joint 6 | 0.01° | 0.05° | 1.0000 |

---

## 3. Cartesian Trajectory Correlation

- **X Correlation ($r_x$):** `0.0`
- **Y Correlation ($r_y$):** `1.0`
- **Z Correlation ($r_z$):** `0.0`

---

## 4. Offscreen Camera Rendering Verification

- **Wrist Synthetic Camera Resolution:** `[240, 320, 3]`
- **Depth Measurement Bounds:** `[0.021, 62.05] m`
- **Data Origin Label:** `SIMULATION_MUJOCO` (Strictly segregated from physical hardware logs).
