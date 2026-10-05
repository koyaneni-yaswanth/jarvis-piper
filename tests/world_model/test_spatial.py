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
