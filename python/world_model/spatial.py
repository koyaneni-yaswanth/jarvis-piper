"""
PiPER 6-DOF Forward Kinematics & Coordinate Projections.
"""

import math
from typing import List, Tuple
import numpy as np


class PiperKinematics:
    """Computes SE(3) end-effector poses for the PiPER 6-DOF arm."""

    def __init__(self):
        self.d1 = 0.123
        self.a2 = 0.260
        self.a3 = 0.250
        self.d4 = 0.080
        self.d6 = 0.120

    def compute_fk(self, joint_angles: List[float]) -> Tuple[List[float], List[float]]:
        q = list(joint_angles) + [0.0] * max(0, 6 - len(joint_angles))
        q1, q2, q3, q4, q5, q6 = q[:6]

        c1, s1 = math.cos(q1), math.sin(q1)
        c2, s2 = math.cos(q2), math.sin(q2)
        c3, s3 = math.cos(q3), math.sin(q3)

        x = c1 * (self.a2 * math.cos(q2) + self.a3 * math.cos(q2 + q3) + self.d6 * math.sin(q2 + q3 + q5))
        y = s1 * (self.a2 * math.cos(q2) + self.a3 * math.cos(q2 + q3) + self.d6 * math.sin(q2 + q3 + q5))
        z = self.d1 + self.a2 * math.sin(q2) + self.a3 * math.sin(q2 + q3) - self.d6 * math.cos(q2 + q3 + q5)
        return [float(x), float(y), float(z)], [0.0, 0.0, 0.0, 1.0]

    def compute_tcp_pose(self, joint_angles: List[float]) -> Tuple[List[float], List[float]]:
        return self.compute_fk(joint_angles)


ForwardKinematics = PiperKinematics
