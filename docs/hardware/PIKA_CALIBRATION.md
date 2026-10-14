# PIKA Sense & Base Station: Spatial Calibration & Tracking Validation

This document describes the spatial calibration lifecycle, mathematical validation criteria, configuration file structure, and diagnostic procedures for the PIKA optical tracking system.

---

## 1. Calibration Lifecycle States

The JARVIS architecture enforces a strict calibration state machine (`jarvis.pika_discovery.CalibrationStatus`). Only the `CALIBRATED` state permits teleoperation command streams:

| State | Definition | Permitted in Milestone 2? |
| :--- | :--- | :--- |
| `NOT_CONFIGURED` | No `config.json` exists; receiver/hardware unconfigured. | **READ-ONLY / AUDIT ONLY** |
| `NOT_CALIBRATED` | Config file exists, but base station poses are zero or identity. | **READ-ONLY / AUDIT ONLY** |
| `CALIBRATED` | Valid base station extrinsics and tracking matrix verified. | **VERIFIED (Mock & Passive Only)** |
| `INVALID` | Corrupted JSON, NaN coefficients, or excessive variance. | **BLOCKED** |
| `STALE` | Timestamp older than 24 hours or physical stations bumped. | **BLOCKED** |
| `UNAVAILABLE` | Receiver dongle disconnected or libsurvive daemon offline. | **BLOCKED** |

---

## 2. libsurvive Optical Calibration Configuration

libsurvive stores tracking configurations in `~/.config/libsurvive/config.json`.

A valid `config.json` contains:
```json
{
  "LighthouseSys": {
    "LH_0": [0.852, -1.243, 1.845, 0.231, -0.412, 0.781, 0.403],
    "LH_1": [-1.102, 1.451, 1.912, -0.198, 0.512, -0.384, 0.745]
  },
  "Pose": {
    "Pos": [0.0, 0.0, 0.0],
    "Rot": [1.0, 0.0, 0.0, 0.0]
  }
}
```

### Automatic Validation Criteria:
1. `Lighthouse` or `LighthouseSys` key must exist and be non-empty.
2. At least two distinct lighthouse entries (`LH_0`, `LH_1`) must have non-zero Cartesian translation ($|x| + |y| + |z| > 0.01$).
3. Rotation coordinates must form valid unit quaternions ($\left| \sum q_i^2 - 1.0 \right| < 0.05$).

---

## 3. Pose Tracking Validation Criteria (`TrackingValidator`)

During real-time streaming, every 6-DOF tracking packet from PIKA Sense must pass all criteria in `jarvis.pika_discovery.TrackingValidator`:

1. **Signal Freshness**: Telemetry packet age $\Delta t \le 50\,\text{ms}$. If $\Delta t > 50\,\text{ms}$, `TrackingLostError` is raised.
2. **Quaternion Normalization**: Orientation $[q_w, q_x, q_y, q_z]$ must satisfy:
   $$|q_w^2 + q_x^2 + q_y^2 + q_z^2 - 1.0| \le 0.05$$
3. **Finite Real Values**: Neither position nor orientation may contain `NaN` or `Inf`.
4. **Non-Identity Fallback**: Pose must not be an uninitialized identity $[0, 0, 0, 1, 0, 0, 0]$ unless the device is at origin and confirmed calibrated.
5. **Base Station Tracking Lock**: Both optical base stations must maintain line of sight with no optical sensor dropouts.

---

## 4. Calibration Execution Procedure (Offline / Phase 0-4)

To run spatial calibration using the open-source libsurvive engine:
```bash
# 1. Place PIKA Sense stationary on the calibration fixture on the workbench.
# 2. Ensure clear line of sight to both Base Stations.
# 3. Run libsurvive calibration CLI:
survive-cli --force-calibrate
```

Once calibrated, run the JARVIS verification tool:
```bash
python -c "
from jarvis.pika_discovery import PikaDiscovery, TrackingValidator
status, info = PikaDiscovery.check_calibration()
print('Calibration Status:', status)
print('Base Stations Found:', info.get('base_stations_found', 0))
"
```
Output:
```text
Calibration Status: CalibrationStatus.CALIBRATED
Base Stations Found: 2
```
If calibration status is anything other than `CALIBRATED`, teleoperation gateways will reject commands with `CalibrationStatusError`.
