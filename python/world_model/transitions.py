"""
JARVIS-PiPER MDP Transition Generator.
"""

from typing import Any, Dict, List
import numpy as np


class TransitionGenerator:
    """Builds (s_t, a_t, r_t, s_{t+1}) transition matrices for Offline RL and World Model learning."""

    def build(self, episode_dict: Dict[str, Any]) -> Dict[str, np.ndarray]:
        steps = episode_dict.get("timesteps", [])
        if len(steps) < 2:
            raise ValueError("Episode contains less than 2 steps.")

        T = len(steps)
        obs = np.zeros((T, 14), dtype=np.float32)
        acts = np.zeros((T, 7), dtype=np.float32)

        for t, s in enumerate(steps):
            q = s.get("joint_positions", [0.0]*6)[:6]
            stroke = s.get("gripper_stroke", 0.035)
            tcp = s.get("tcp_pose", {}).get("position", [0.0, 0.0, 0.0])[:3]
            quat = s.get("tcp_pose", {}).get("orientation", [0.0, 0.0, 0.0, 1.0])[:4]

            obs[t, :6] = q
            obs[t, 6] = stroke
            obs[t, 7:10] = tcp
            obs[t, 10:14] = quat

            acts[t, :6] = s.get("action", q)[:6]
            acts[t, 6] = stroke

        rewards = np.zeros((T - 1, 1), dtype=np.float32)
        rewards[-1, 0] = 1.0 if episode_dict.get("metadata", {}).get("success_label", True) else 0.0

        return {
            "observations": obs[:-1],
            "actions": acts[:-1],
            "rewards": rewards,
            "next_observations": obs[1:],
            "terminals": np.array([[1.0 if i == T-2 else 0.0] for i in range(T-1)], dtype=np.float32),
        }
