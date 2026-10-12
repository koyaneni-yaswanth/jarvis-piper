#!/usr/bin/env python3
"""
Audits authoritative PiPER URDF and validates forward/inverse kinematics against known targets.
"""

import os
import sys
import numpy as np

sys.path.insert(0, "python")
from world_model.spatial import PiperKinematics


def run_robot_model_audit():
    print("=" * 80)
    print("          AGILEX PIPER ROBOT MODEL & DIGITAL TWIN AUDIT")
    print("=" * 80)

    urdf_path = "ros2_ws/src/jarvis_piper_bringup/urdf/piper.urdf"
    xacro_path = "ros2_ws/src/jarvis_piper_bringup/urdf/piper.urdf.xacro"

    print("1. Checking URDF / Xacro asset existence:")
    assert os.path.exists(urdf_path), f"Missing URDF at {urdf_path}"
    assert os.path.exists(xacro_path), f"Missing Xacro at {xacro_path}"
    print(f"   [PASS] Found URDF ({os.path.getsize(urdf_path)} bytes)")
    print(f"   [PASS] Found Xacro ({os.path.getsize(xacro_path)} bytes)")

    print("\n2. Validating 6-DOF Kinematic Solvers:")
    fk = PiperKinematics()

    # Zero pose
    pos_zero, quat_zero = fk.compute_fk([0.0] * 6)
    print(f"   Zero Pose TCP:     {[round(x, 4) for x in pos_zero]}")
    assert pos_zero[2] > 0.30, "Z-height invalid at upright zero pose"

    # Forward reach test
    q_reach = [0.0, 0.6, -1.0, 0.0, 0.4, 0.0]
    pos_reach, _ = fk.compute_fk(q_reach)
    print(f"   Forward Reach TCP: {[round(x, 4) for x in pos_reach]}")

    # Inverse Kinematics Reachability
    q_sol, success = fk.compute_ik(pos_reach, q_init=[0.0, 0.5, -0.8, 0.0, 0.0, 0.0])
    assert success and q_sol is not None, "IK solver failed to converge on known reachable target"
    pos_achieved, _ = fk.compute_fk(q_sol)
    pos_err = np.linalg.norm(np.array(pos_reach) - np.array(pos_achieved))
    print(f"   IK Re-convergence Error: {pos_err:7.5f} m (Target < 0.005 m)")
    assert pos_err < 0.005, "IK error exceeds tolerance"

    print("\n" + "=" * 80)
    print(" [PASSED] Robot Model and Kinematic Validation Audit Successful!")
    print("=" * 80)
    return 0


if __name__ == "__main__":
    sys.exit(run_robot_model_audit())
