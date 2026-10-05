"""
JARVIS PiPER 3D Spatial State & Forward Kinematics Engine
Computes SE(3) forward kinematics, end-effector poses, twists, and coordinate projections.
"""

import math
from typing import Dict, List, Tuple
import numpy as np


def rot_x(theta: float) -> np.ndarray:
    c, s = math.cos(theta), math.sin(theta)
    return np.array([
        [1.0, 0.0, 0.0, 0.0],
        [0.0, c, -s, 0.0],
        [0.0, s, c, 0.0],
        [0.0, 0.0, 0.0, 1.0],
    ])


def rot_y(theta: float) -> np.ndarray:
    c, s = math.cos(theta), math.sin(theta)
    return np.array([
        [c, 0.0, s, 0.0],
        [0.0, 1.0, 0.0, 0.0],
        [-s, 0.0, c, 0.0],
        [0.0, 0.0, 0.0, 1.0],
    ])


def rot_z(theta: float) -> np.ndarray:
    c, s = math.cos(theta), math.sin(theta)
    return np.array([
        [c, -s, 0.0, 0.0],
        [s, c, 0.0, 0.0],
        [0.0, 0.0, 1.0, 0.0],
        [0.0, 0.0, 0.0, 1.0],
    ])


def trans(x: float, y: float, z: float) -> np.ndarray:
    T = np.eye(4)
    T[0, 3] = x
    T[1, 3] = y
    T[2, 3] = z
    return T


def rot_matrix_to_quaternion(R: np.ndarray) -> List[float]:
    """Converts 3x3 rotation matrix to quaternion [x, y, z, w]."""
    tr = R[0, 0] + R[1, 1] + R[2, 2]
    if tr > 0:
        S = math.sqrt(tr + 1.0) * 2
        w = 0.25 * S
        x = (R[2, 1] - R[1, 2]) / S
        y = (R[0, 2] - R[2, 0]) / S
        z = (R[1, 0] - R[0, 1]) / S
    elif (R[0, 0] > R[1, 1]) and (R[0, 0] > R[2, 2]):
        S = math.sqrt(1.0 + R[0, 0] - R[1, 1] - R[2, 2]) * 2
        w = (R[2, 1] - R[1, 2]) / S
        x = 0.25 * S
        y = (R[0, 1] + R[1, 0]) / S
        z = (R[0, 2] + R[2, 0]) / S
    elif R[1, 1] > R[2, 2]:
        S = math.sqrt(1.0 + R[1, 1] - R[0, 0] - R[2, 2]) * 2
        w = (R[0, 2] - R[2, 0]) / S
        x = (R[0, 1] + R[1, 0]) / S
        y = 0.25 * S
        z = (R[1, 2] + R[2, 1]) / S
    else:
        S = math.sqrt(1.0 + R[2, 2] - R[0, 0] - R[1, 1]) * 2
        w = (R[1, 0] - R[0, 1]) / S
        x = (R[0, 2] + R[2, 0]) / S
        y = (R[1, 2] + R[2, 1]) / S
        z = 0.25 * S
    return [float(x), float(y), float(z), float(w)]


class PiperForwardKinematics:
    """Analytical 6-DOF Forward Kinematics for PiPER robotic manipulator."""

    def __init__(self):
        # PiPER kinematic parameters (meters)
        self.d1 = 0.123  # Base to shoulder
        self.a2 = 0.260  # Upper arm length
        self.a3 = 0.250  # Forearm length
        self.d4 = 0.080  # Wrist offset
        self.d6 = 0.120  # Tool center point (TCP) offset including gripper

    def compute_fk(self, joint_angles: List[float]) -> Tuple[List[float], List[float]]:
        """
        Computes forward kinematics for PiPER 6-DOF arm.
        Returns:
            position: [x, y, z] in robot base frame (meters)
            quaternion: [x, y, z, w] orientation
        """
        q = list(joint_angles) + [0.0] * max(0, 6 - len(joint_angles))
        q1, q2, q3, q4, q5, q6 = q[:6]

        T = np.eye(4)
        # Joint 1: Base yaw
        T = T @ rot_z(q1) @ trans(0, 0, self.d1)
        # Joint 2: Shoulder pitch
        T = T @ rot_y(q2) @ trans(0, 0, self.a2)
        # Joint 3: Elbow pitch
        T = T @ rot_y(q3) @ trans(0, 0, self.a3)
        # Joint 4: Wrist roll
        T = T @ rot_z(q4) @ trans(0, 0, self.d4)
        # Joint 5: Wrist pitch
        T = T @ rot_y(q5)
        # Joint 6: Wrist roll & End Effector TCP
        T = T @ rot_z(q6) @ trans(0, 0, self.d6)

        pos = [float(T[0, 3]), float(T[1, 3]), float(T[2, 3])]
        quat = rot_matrix_to_quaternion(T[:3, :3])
        return pos, quat
