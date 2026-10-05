"""
SE(3) 3D Spatial and Kinematics Transformation Utilities.
Converts between Euler angles, Quaternions, and 4x4 Homogeneous Transformation Matrices.
"""

import math
import numpy as np
from typing import Tuple, List, Union


def euler_to_quaternion(roll: float, pitch: float, yaw: float) -> Tuple[float, float, float, float]:
    """
    Converts Roll, Pitch, Yaw (radians, XYZ order) to Quaternion (x, y, z, w).
    """
    cr = math.cos(roll * 0.5)
    sr = math.sin(roll * 0.5)
    cp = math.cos(pitch * 0.5)
    sp = math.sin(pitch * 0.5)
    cy = math.cos(yaw * 0.5)
    sy = math.sin(yaw * 0.5)

    w = cr * cp * cy + sr * sp * sy
    x = sr * cp * cy - cr * sp * sy
    y = cr * sp * cy + sr * cp * sy
    z = cr * cp * sy - sr * sp * cy

    return (x, y, z, w)


def quaternion_to_euler(x: float, y: float, z: float, w: float) -> Tuple[float, float, float]:
    """
    Converts Quaternion (x, y, z, w) to Roll, Pitch, Yaw (radians).
    """
    # Roll (x-axis rotation)
    sinr_cosp = 2.0 * (w * x + y * z)
    cosr_cosp = 1.0 - 2.0 * (x * x + y * y)
    roll = math.atan2(sinr_cosp, cosr_cosp)

    # Pitch (y-axis rotation)
    sinp = 2.0 * (w * y - z * x)
    if abs(sinp) >= 1:
        pitch = math.copysign(math.pi / 2.0, sinp)
    else:
        pitch = math.asin(sinp)

    # Yaw (z-axis rotation)
    siny_cosp = 2.0 * (w * z + x * y)
    cosy_cosp = 1.0 - 2.0 * (y * y + z * z)
    yaw = math.atan2(siny_cosp, cosy_cosp)

    return (roll, pitch, yaw)


def euler_to_rotation_matrix(roll: float, pitch: float, yaw: float) -> np.ndarray:
    """3x3 Rotation Matrix from Roll, Pitch, Yaw."""
    Rx = np.array([
        [1, 0, 0],
        [0, math.cos(roll), -math.sin(roll)],
        [0, math.sin(roll), math.cos(roll)]
    ])
    Ry = np.array([
        [math.cos(pitch), 0, math.sin(pitch)],
        [0, 1, 0],
        [-math.sin(pitch), 0, math.cos(pitch)]
    ])
    Rz = np.array([
        [math.cos(yaw), -math.sin(yaw), 0],
        [math.sin(yaw), math.cos(yaw), 0],
        [0, 0, 1]
    ])
    return Rz @ Ry @ Rx


def quaternion_to_rotation_matrix(q: Union[Tuple[float, float, float, float], List[float], np.ndarray]) -> np.ndarray:
    """3x3 Rotation Matrix from Quaternion (x, y, z, w)."""
    x, y, z, w = q
    return np.array([
        [1.0 - 2.0*(y*y + z*z), 2.0*(x*y - z*w),       2.0*(x*z + y*w)],
        [2.0*(x*y + z*w),       1.0 - 2.0*(x*x + z*z), 2.0*(y*z - x*w)],
        [2.0*(x*z - y*w),       2.0*(y*z + x*w),       1.0 - 2.0*(x*x + y*y)],
    ])


def create_transform_matrix(
    translation: Union[List[float], Tuple[float, float, float], np.ndarray],
    rotation: Union[List[float], Tuple[float, float, float], np.ndarray],  # quaternion (x,y,z,w) or R (3x3)
) -> np.ndarray:
    """
    Creates a 4x4 SE(3) homogeneous transformation matrix.
    """
    T = np.eye(4, dtype=np.float64)
    T[0:3, 3] = translation

    rot = np.asarray(rotation)
    if rot.shape == (3, 3):
        T[0:3, 0:3] = rot
    elif rot.size == 4:
        T[0:3, 0:3] = quaternion_to_rotation_matrix(rot)
    elif rot.size == 3:
        T[0:3, 0:3] = euler_to_rotation_matrix(rot[0], rot[1], rot[2])

    return T


def invert_transform_matrix(T: np.ndarray) -> np.ndarray:
    """Computes exact inverse of a 4x4 SE(3) transformation matrix."""
    R = T[0:3, 0:3]
    t = T[0:3, 3]
    T_inv = np.eye(4, dtype=np.float64)
    T_inv[0:3, 0:3] = R.T
    T_inv[0:3, 3] = -R.T @ t
    return T_inv


def transform_point(T: np.ndarray, point: Union[List[float], np.ndarray]) -> np.ndarray:
    """Applies 4x4 transformation matrix T to a 3D point [x, y, z]."""
    p_homo = np.array([point[0], point[1], point[2], 1.0])
    p_out = T @ p_homo
    return p_out[0:3]
