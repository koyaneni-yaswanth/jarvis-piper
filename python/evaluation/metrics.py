"""
Evaluation and Quality Metrics for Trajectories, Synchronization, and Teleoperation.
"""

import numpy as np
from typing import Dict, List, Any


def compute_trajectory_jerk(joint_positions: np.ndarray, dt: float = 0.02) -> float:
    """
    Computes mean third derivative (jerk) of joint trajectories.
    Lower jerk indicates smoother teleoperation and better demonstration quality.
    """
    if len(joint_positions) < 4:
        return 0.0

    # 1st deriv: velocity
    vel = np.gradient(joint_positions, dt, axis=0)
    # 2nd deriv: acceleration
    acc = np.gradient(vel, dt, axis=0)
    # 3rd deriv: jerk
    jerk = np.gradient(acc, dt, axis=0)

    # Return root-mean-squared jerk across all joints
    return float(np.sqrt(np.mean(jerk ** 2)))


def compute_sync_jitter(timestamps: List[float], expected_hz: float = 50.0) -> Dict[str, float]:
    """
    Computes jitter (standard deviation of inter-frame delta) and dropped frames.
    """
    if len(timestamps) < 2:
        return {"mean_dt_ms": 0.0, "jitter_std_ms": 0.0, "max_gap_ms": 0.0, "drop_ratio": 0.0}

    ts = np.array(timestamps)
    diffs = np.diff(ts)
    expected_dt = 1.0 / expected_hz

    jitter_std = np.std(diffs)
    mean_dt = np.mean(diffs)
    max_gap = np.max(diffs)

    # Consider anything > 2.0 * expected_dt as dropped frames
    dropped = np.sum(diffs > (1.8 * expected_dt))
    drop_ratio = dropped / max(1, len(diffs))

    return {
        "mean_dt_ms": float(mean_dt * 1000.0),
        "jitter_std_ms": float(jitter_std * 1000.0),
        "max_gap_ms": float(max_gap * 1000.0),
        "drop_ratio": float(drop_ratio),
    }


def compute_gripper_efficiency(gripper_positions: np.ndarray) -> Dict[str, Any]:
    """
    Computes gripper chattering and grasp stability.
    """
    if len(gripper_positions) < 2:
        return {"chatter_count": 0, "is_stable": True}

    diffs = np.diff(gripper_positions)
    # Sign changes indicate direction reversals
    signs = np.sign(diffs)
    sign_changes = np.sum(np.diff(signs) != 0)

    return {
        "reversals": int(sign_changes),
        "is_stable": bool(sign_changes < 15),
    }
