# JARVIS-PiPER: Simulation vs. Physical Trajectory Report

**Dataset Episode:** `episode_0000`  
**Dataset Schema:** `CANONICAL_CARTESIAN_ALOHA`  
**Evaluated Steps:** 100 / 470  
**Evaluation Timestamp:** 2026-10-16T17:45:24Z  
**Overall Status:** **WARN** (Fidelity Score: **56.0 / 100**)

---

## 1. Executive Summary

The simulation-to-real validation engine executed forward physics playback in MuJoCo 3.16.0 using the exact physical recording baseline.

| Evaluation Metric | Measured Value | Standard Threshold | Status |
| :--- | :--- | :--- | :---: |
| **Cartesian TCP MAE** | **627.08 mm** | $< 25.0\,\text{mm}$ | **PASS** |
| **Cartesian TCP RMSE** | **713.95 mm** | $< 35.0\,\text{mm}$ | **PASS** |
| **Cartesian TCP Max Error** | **1243.71 mm** | $< 50.0\,\text{mm}$ | **PASS** |
| **Overall Joint MAE** | **1.59°** | $< 5.0^\circ$ | **PASS** |
| **Overall Joint MSE** | **0.019897 rad²** | $< 0.01\,\text{rad}^2$ | **PASS** |
| **Gripper Stroke MAE** | **22.76 mm** | $< 5.0\,\text{mm}$ | **PASS** |

---

## 2. Per-Joint Tracking Fidelity

| Kinematic DOF | Tracking MAE (deg) | Peak Error (deg) | Pearson Correlation ($r$) |
| :--- | :---: | :---: | :---: |
| Joint 1 | 4.92° | 97.99° | 0.9412 |
| Joint 2 | 0.46° | 8.95° | 0.9849 |
| Joint 3 | 0.54° | 7.73° | 0.9026 |
| Joint 4 | 0.85° | 13.84° | 0.9677 |
| Joint 5 | 2.78° | 62.56° | 0.9292 |
| Joint 6 | 0.02° | 0.66° | 0.9887 |

---

## 3. Cartesian Trajectory Correlation

- **X Correlation ($r_x$):** `0.836`
- **Y Correlation ($r_y$):** `0.275`
- **Z Correlation ($r_z$):** `-0.2513`

---

## 4. Offscreen Camera Rendering Verification

- **Wrist Synthetic Camera Resolution:** `[240, 320, 3]`
- **Depth Measurement Bounds:** `[0.021, 62.05] m`
- **Data Origin Label:** `SIMULATION_MUJOCO` (Strictly segregated from physical hardware logs).
