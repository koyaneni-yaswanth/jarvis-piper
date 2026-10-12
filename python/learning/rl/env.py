"""
Gym-compatible Target Reaching Environment for AgileX PiPER 6-DOF Manipulator.
Simulates kinematics, joint limits, target generation, and distance rewards.
"""

import math
from typing import Dict, Optional, Tuple
import numpy as np

from world_model.spatial import PiperKinematics


class PiperReachEnv:
    """
    Continuous control environment for reaching random 3D targets in the forward workspace.
    Observation (19D): [q_1..6 (6), q_dot_1..6 (6), tcp_pos (3), stroke (1), target_pos (3)]
    Action (6D): Delta joint positions in radians [-0.05, 0.05]
    """

    def __init__(self, max_steps: int = 100, dt: float = 0.02):
        self.kinematics = PiperKinematics()
        self.max_steps = max_steps
        self.dt = dt
        self.step_count = 0

        self.q = np.array([0.0, 0.5, -0.5, 0.0, 0.0, 0.0], dtype=np.float64)
        self.q_dot = np.zeros(6, dtype=np.float64)
        self.target_pos = np.array([0.35, 0.0, 0.25], dtype=np.float64)
        self.stroke = 0.035

    def reset(self, seed: Optional[int] = None) -> np.ndarray:
        if seed is not None:
            np.random.seed(seed)
        self.step_count = 0
        self.q = np.array([0.0, 0.5, -0.5, 0.0, 0.0, 0.0], dtype=np.float64)
        self.q_dot = np.zeros(6, dtype=np.float64)

        # Random reachable target in forward workspace
        tx = float(np.random.uniform(0.25, 0.45))
        ty = float(np.random.uniform(-0.20, 0.20))
        tz = float(np.random.uniform(0.15, 0.35))
        self.target_pos = np.array([tx, ty, tz], dtype=np.float64)

        return self._get_obs()

    def _get_obs(self) -> np.ndarray:
        tcp_pos, _ = self.kinematics.compute_fk(list(self.q))
        obs = np.concatenate([
            self.q,
            self.q_dot,
            np.array(tcp_pos, dtype=np.float64),
            [self.stroke],
            self.target_pos,
        ]).astype(np.float32)
        return obs

    def step(self, action: np.ndarray) -> Tuple[np.ndarray, float, bool, Dict]:
        self.step_count += 1
        delta_q = np.clip(np.asarray(action, dtype=np.float64)[:6], -0.05, 0.05)

        self.q_dot = delta_q / self.dt
        self.q += delta_q

        # Enforce physical joint limits
        for j in range(6):
            low, high = self.kinematics.JOINT_LIMITS[j]
            self.q[j] = np.clip(self.q[j], low, high)

        tcp_pos, _ = self.kinematics.compute_fk(list(self.q))
        dist = float(np.linalg.norm(np.array(tcp_pos) - self.target_pos))

        # Reward formulation
        reward = -2.0 * dist - 0.01 * float(np.sum(delta_q ** 2))
        reached = dist < 0.02
        if reached:
            reward += 50.0

        done = reached or (self.step_count >= self.max_steps)
        info = {"dist": dist, "reached": reached, "step": self.step_count}

        return self._get_obs(), float(reward), bool(done), info
