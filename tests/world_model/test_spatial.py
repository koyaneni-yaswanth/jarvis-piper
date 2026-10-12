"""
Unit tests for forward kinematics and spatial projections.
"""

import numpy as np
from world_model.spatial import PiperKinematics, ForwardKinematics


def test_piper_kinematics():
    fk = PiperKinematics()
    q_zero = [0.0] * 6
    pos, quat = fk.compute_fk(q_zero)
    assert len(pos) == 3
    assert len(quat) == 4
    # At zero configuration, arm is upright/extended
    assert pos[0] > 0.0 or pos[2] > 0.0


def test_forward_kinematics_alias():
    fk = ForwardKinematics()
    q = [0.1, -0.2, 0.3, 0.0, 0.0, 0.0]
    pos, quat = fk.compute_tcp_pose(q)
    assert len(pos) == 3
    assert len(quat) == 4


def test_jacobian_computation():
    fk = PiperKinematics()
    q = [0.0, 0.5, -0.5, 0.1, -0.1, 0.0]
    J = fk.compute_jacobian(q)
    assert J.shape == (6, 6)
    assert not np.isnan(J).any()
    assert not np.isinf(J).any()


def test_inverse_kinematics_reachability():
    fk = PiperKinematics()
    q_target = [0.2, 0.6, -0.8, 0.1, 0.2, 0.0]
    pos_target, _ = fk.compute_fk(q_target)

    # Solve IK from different initial seed
    q_sol, success = fk.compute_ik(pos_target, q_init=[0.0, 0.4, -0.4, 0.0, 0.0, 0.0])
    assert q_sol is not None
    pos_achieved, _ = fk.compute_fk(q_sol)
    pos_err = np.linalg.norm(np.array(pos_target) - np.array(pos_achieved))
    assert pos_err < 0.01  # Sub-centimeter convergence

