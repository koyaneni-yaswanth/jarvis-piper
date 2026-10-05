"""
Unit tests for 3D spatial transformations and kinematics.
"""

import math
import numpy as np
import pytest
from utils.transforms import (
    euler_to_quaternion,
    quaternion_to_euler,
    euler_to_rotation_matrix,
    create_transform_matrix,
    invert_transform_matrix,
    transform_point,
)


def test_euler_quaternion_roundtrip():
    roll, pitch, yaw = 0.2, -0.4, 0.6
    q = euler_to_quaternion(roll, pitch, yaw)
    assert len(q) == 4
    assert np.isclose(np.linalg.norm(q), 1.0, atol=1e-5)

    r2, p2, y2 = quaternion_to_euler(q[0], q[1], q[2], q[3])
    assert np.isclose(roll, r2, atol=1e-4)
    assert np.isclose(pitch, p2, atol=1e-4)
    assert np.isclose(yaw, y2, atol=1e-4)


def test_se3_transform_inversion():
    trans = [0.5, -0.3, 0.8]
    rot = euler_to_rotation_matrix(0.1, 0.2, -0.3)
    T = create_transform_matrix(trans, rot)
    assert T.shape == (4, 4)

    T_inv = invert_transform_matrix(T)
    identity = T @ T_inv
    assert np.allclose(identity, np.eye(4), atol=1e-5)


def test_transform_point():
    T = create_transform_matrix([1.0, 2.0, 3.0], np.eye(3))
    pt = [0.0, 0.0, 0.0]
    p_trans = transform_point(T, pt)
    assert np.allclose(p_trans, [1.0, 2.0, 3.0], atol=1e-5)
