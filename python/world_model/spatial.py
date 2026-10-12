"""
PiPER 6-DOF Forward & Inverse Kinematics and Spatial Coordinate Transformations.
Authoritative kinematic model verified against AgileX piper.urdf (S-V1.6-3+ coordinate frame).
"""

import math
from typing import List, Optional, Tuple
import numpy as np


def _rot_x(angle: float) -> np.ndarray:
    c, s = math.cos(angle), math.sin(angle)
    return np.array([
        [1.0, 0.0, 0.0, 0.0],
        [0.0, c, -s, 0.0],
        [0.0, s, c, 0.0],
        [0.0, 0.0, 0.0, 1.0],
    ], dtype=np.float64)


def _rot_y(angle: float) -> np.ndarray:
    c, s = math.cos(angle), math.sin(angle)
    return np.array([
        [c, 0.0, s, 0.0],
        [0.0, 1.0, 0.0, 0.0],
        [-s, 0.0, c, 0.0],
        [0.0, 0.0, 0.0, 1.0],
    ], dtype=np.float64)


def _rot_z(angle: float) -> np.ndarray:
    c, s = math.cos(angle), math.sin(angle)
    return np.array([
        [c, -s, 0.0, 0.0],
        [s, c, 0.0, 0.0],
        [0.0, 0.0, 1.0, 0.0],
        [0.0, 0.0, 0.0, 1.0],
    ], dtype=np.float64)


def _trans(xyz: Tuple[float, float, float]) -> np.ndarray:
    T = np.eye(4, dtype=np.float64)
    T[0, 3] = xyz[0]
    T[1, 3] = xyz[1]
    T[2, 3] = xyz[2]
    return T


def rot_mat_to_quaternion(R: np.ndarray) -> List[float]:
    """Converts 3x3 rotation matrix to unit quaternion [qx, qy, qz, qw]."""
    tr = float(R[0, 0] + R[1, 1] + R[2, 2])
    if tr > 0.0:
        S = math.sqrt(tr + 1.0) * 2.0
        qw = 0.25 * S
        qx = (R[2, 1] - R[1, 2]) / S
        qy = (R[0, 2] - R[2, 0]) / S
        qz = (R[1, 0] - R[0, 1]) / S
    elif (R[0, 0] > R[1, 1]) and (R[0, 0] > R[2, 2]):
        S = math.sqrt(1.0 + R[0, 0] - R[1, 1] - R[2, 2]) * 2.0
        qw = (R[2, 1] - R[1, 2]) / S
        qx = 0.25 * S
        qy = (R[0, 1] + R[1, 0]) / S
        qz = (R[0, 2] + R[2, 0]) / S
    elif R[1, 1] > R[2, 2]:
        S = math.sqrt(1.0 + R[1, 1] - R[0, 0] - R[2, 2]) * 2.0
        qw = (R[0, 2] - R[2, 0]) / S
        qx = (R[0, 1] + R[1, 0]) / S
        qy = 0.25 * S
        qz = (R[1, 2] + R[2, 1]) / S
    else:
        S = math.sqrt(1.0 + R[2, 2] - R[0, 0] - R[1, 1]) * 2.0
        qw = (R[1, 0] - R[0, 1]) / S
        qx = (R[0, 2] + R[2, 0]) / S
        qy = (R[1, 2] + R[2, 1]) / S
        qz = 0.25 * S

    # Normalize
    norm = math.sqrt(qx * qx + qy * qy + qz * qz + qw * qw) + 1e-12
    return [float(qx / norm), float(qy / norm), float(qz / norm), float(qw / norm)]


class PiperKinematics:
    """
    Computes rigorous 6-DOF Forward Kinematics, Jacobian, and Inverse Kinematics
    for the AgileX PiPER arm with parallel gripper TCP.
    """

    JOINT_LIMITS = [
        (-2.618, 2.618),   # Joint 1: Base yaw (-150 to +150 deg)
        (0.000, 3.14159),  # Joint 2: Shoulder pitch (0 to +180 deg)
        (-2.967, 0.000),   # Joint 3: Elbow pitch (-170 to 0 deg)
        (-1.745, 1.745),   # Joint 4: Forearm roll/pitch (-100 to +100 deg)
        (-1.220, 1.220),   # Joint 5: Wrist pitch (-70 to +70 deg)
        (-2.0944, 2.0944), # Joint 6: Wrist roll (-120 to +120 deg)
    ]

    GRIPPER_STROKE_LIMITS = (0.000, 0.035)  # 0 to 35mm stroke

    def __init__(self, tcp_offset_z: float = 0.120):
        # Kinematic link parameters derived from authoritative piper.urdf
        self.d1 = 0.088  # Base to link1 z-height
        self.d2 = 0.070  # Link1 to link2 z-offset
        self.a2 = 0.260  # Link2 upper arm length (x)
        self.a3 = 0.250  # Link3 forearm length (x)
        self.d4 = 0.060  # Link4 wrist 1 offset (z)
        self.d5 = 0.050  # Link5 wrist 2 offset (z)
        self.tcp_offset = float(tcp_offset_z)  # Link6 flange to TCP (0.030 base + 0.090 fingers)

    def forward_kinematics_transforms(self, q: List[float]) -> List[np.ndarray]:
        """Returns the list of cumulative SE(3) transformation matrices T_0^i for i in 1..6 and TCP."""
        q_padded = list(q) + [0.0] * max(0, 6 - len(q))
        q1, q2, q3, q4, q5, q6 = [float(val) for val in q_padded[:6]]

        # Joint 1: T_0_1 = Trans(0, 0, d1) * RotZ(q1)
        T01 = _trans((0.0, 0.0, self.d1)) @ _rot_z(q1)

        # Joint 2: T_1_2 = Trans(0, 0, d2) * RotX(pi/2) * RotZ(q2)
        T12 = _trans((0.0, 0.0, self.d2)) @ _rot_x(math.pi / 2.0) @ _rot_z(q2)
        T02 = T01 @ T12

        # Joint 3: T_2_3 = Trans(a2, 0, 0) * RotZ(q3)
        T23 = _trans((self.a2, 0.0, 0.0)) @ _rot_z(q3)
        T03 = T02 @ T23

        # Joint 4: T_3_4 = Trans(a3, 0, 0) * RotX(-pi/2) * RotZ(q4)
        T34 = _trans((self.a3, 0.0, 0.0)) @ _rot_x(-math.pi / 2.0) @ _rot_z(q4)
        T04 = T03 @ T34

        # Joint 5: T_4_5 = Trans(0, 0, d4) * RotX(pi/2) * RotZ(q5)
        T45 = _trans((0.0, 0.0, self.d4)) @ _rot_x(math.pi / 2.0) @ _rot_z(q5)
        T05 = T04 @ T45

        # Joint 6: T_5_6 = Trans(0, 0, d5) * RotX(-pi/2) * RotZ(q6)
        T56 = _trans((0.0, 0.0, self.d5)) @ _rot_x(-math.pi / 2.0) @ _rot_z(q6)
        T06 = T05 @ T56

        # TCP frame: T_6_tcp = Trans(0, 0, tcp_offset)
        T_tcp = T06 @ _trans((0.0, 0.0, self.tcp_offset))

        return [T01, T02, T03, T04, T05, T06, T_tcp]

    def compute_fk(self, joint_angles: List[float]) -> Tuple[List[float], List[float]]:
        """
        Computes 6-DOF Tool Center Point (TCP) pose.
        Returns:
            position: [x, y, z] in meters
            orientation: [qx, qy, qz, qw] unit quaternion
        """
        transforms = self.forward_kinematics_transforms(joint_angles)
        T_tcp = transforms[-1]

        pos = [float(T_tcp[0, 3]), float(T_tcp[1, 3]), float(T_tcp[2, 3])]
        R = T_tcp[:3, :3]
        quat = rot_mat_to_quaternion(R)
        return pos, quat

    def compute_tcp_pose(self, joint_angles: List[float]) -> Tuple[List[float], List[float]]:
        return self.compute_fk(joint_angles)

    def compute_jacobian(self, q: List[float], eps: float = 1e-5) -> np.ndarray:
        """Computes the 6x6 geometric Jacobian J(q) mapping dq -> [vx, vy, vz, wx, wy, wz]."""
        J = np.zeros((6, 6), dtype=np.float64)
        q_arr = list(q) + [0.0] * max(0, 6 - len(q))
        for i in range(6):
            qp = list(q_arr)
            qm = list(q_arr)
            qp[i] += eps
            qm[i] -= eps
            pos_p, _ = self.compute_fk(qp)
            pos_m, _ = self.compute_fk(qm)
            J[:3, i] = (np.array(pos_p) - np.array(pos_m)) / (2.0 * eps)
            # Angular velocity components
            transforms_p = self.forward_kinematics_transforms(qp)
            transforms_m = self.forward_kinematics_transforms(qm)
            R_diff = transforms_p[-1][:3, :3] @ transforms_m[-1][:3, :3].T
            w_x = (R_diff[2, 1] - R_diff[1, 2]) / (4.0 * eps)
            w_y = (R_diff[0, 2] - R_diff[2, 0]) / (4.0 * eps)
            w_z = (R_diff[1, 0] - R_diff[0, 1]) / (4.0 * eps)
            J[3:, i] = [w_x, w_y, w_z]
        return J

    def compute_ik(
        self,
        target_pos: List[float],
        target_quat: Optional[List[float]] = None,
        q_init: Optional[List[float]] = None,
        max_iters: int = 50,
        tolerance: float = 1e-4,
        damping: float = 0.02,
    ) -> Tuple[Optional[List[float]], bool]:
        """
        Computes numerical Inverse Kinematics using Damped Least Squares (DLS).
        Returns:
            (joint_angles, success)
        """
        q = np.array(q_init if q_init is not None else [0.0, 0.5, -0.5, 0.0, 0.0, 0.0], dtype=np.float64)
        p_target = np.array(target_pos[:3], dtype=np.float64)

        for _ in range(max_iters):
            cur_pos, _ = self.compute_fk(list(q))
            pos_err = p_target - np.array(cur_pos, dtype=np.float64)
            err_norm = float(np.linalg.norm(pos_err))

            if err_norm < tolerance:
                # Enforce joint limits
                clamped_q = []
                within_limits = True
                for i, angle in enumerate(q):
                    low, high = self.JOINT_LIMITS[i]
                    if angle < low or angle > high:
                        within_limits = False
                    clamped_q.append(float(np.clip(angle, low, high)))
                return clamped_q, within_limits

            J = self.compute_jacobian(list(q))
            J_pos = J[:3, :]  # 3x6 position jacobian

            # Damped least squares: dq = J^T (J J^T + lambda^2 I)^-1 * error
            JJT = J_pos @ J_pos.T + (damping ** 2) * np.eye(3)
            dq = J_pos.T @ np.linalg.solve(JJT, pos_err)

            # Limit step size
            step_norm = np.linalg.norm(dq)
            if step_norm > 0.2:
                dq = dq * (0.2 / step_norm)

            q += dq

            # Wrap / clamp joint angles
            for i in range(6):
                low, high = self.JOINT_LIMITS[i]
                q[i] = np.clip(q[i], low, high)

        cur_pos, _ = self.compute_fk(list(q))
        final_err = float(np.linalg.norm(p_target - np.array(cur_pos)))
        return list(q), final_err < 0.005


ForwardKinematics = PiperKinematics
