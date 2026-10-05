"""
JARVIS PiPER Transition Dataset Builder
Generates Offline RL / World Model transition tuples: (s_t, a_t, r_t, s_{t+1}, terminal).
"""

from typing import Any, Dict, List
import numpy as np


class TransitionDatasetBuilder:
    """Builds pre-indexed MDP state-action-reward-next_state transition dictionaries."""

    def __init__(self, reward_mode: str = "sparse_completion"):
        self.reward_mode = reward_mode

    def build_transitions(self, episode_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Converts episode data dictionary into transition arrays.
        Returns:
            {
                "observations": np.ndarray [T-1, D_obs],
                "actions": np.ndarray [T-1, D_act],
                "rewards": np.ndarray [T-1, 1],
                "next_observations": np.ndarray [T-1, D_obs],
                "terminals": np.ndarray [T-1, 1],
                "language_instruction": str,
            }
        """
        meta = episode_data.get("metadata", {})
        steps = episode_data.get("timesteps", [])
        if len(steps) < 2:
            raise ValueError("Episode contains less than 2 steps; cannot form transition tuples.")

        T = len(steps)
        obs_dim = 14  # 6 joints + 1 gripper + 3 TCP pos + 4 TCP quat
        act_dim = 7   # 6 arm actions + 1 gripper action

        obs_array = np.zeros((T, obs_dim), dtype=np.float32)
        act_array = np.zeros((T, act_dim), dtype=np.float32)

        for t, step in enumerate(steps):
            q = step.get("joint_positions", [0.0] * 6)[:6]
            stroke = step.get("gripper_stroke", 0.035)
            tcp = step.get("tcp_pose", {})
            pos = tcp.get("position", [0.0, 0.0, 0.0])[:3]
            quat = tcp.get("orientation", [0.0, 0.0, 0.0, 1.0])[:4]

            obs_array[t, :6] = q
            obs_array[t, 6] = stroke
            obs_array[t, 7:10] = pos
            obs_array[t, 10:14] = quat

            # Action
            act = step.get("action", q)[:6]
            act_array[t, :6] = act
            act_array[t, 6] = stroke

        # Form transitions
        s_t = obs_array[:-1]
        a_t = act_array[:-1]
        s_next = obs_array[1:]

        rewards = np.zeros((T - 1, 1), dtype=np.float32)
        terminals = np.zeros((T - 1, 1), dtype=np.float32)

        # Final step reward
        success = meta.get("success_label", True)
        if success:
            rewards[-1, 0] = 1.0
        terminals[-1, 0] = 1.0

        return {
            "episode_id": meta.get("episode_id", "unknown"),
            "language_instruction": meta.get("task_instruction", ""),
            "observations": s_t,
            "actions": a_t,
            "rewards": rewards,
            "next_observations": s_next,
            "terminals": terminals,
            "timesteps": T - 1,
        }
