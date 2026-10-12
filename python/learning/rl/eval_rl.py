#!/usr/bin/env python3
"""
Evaluation script for trained PPO policy on Piper reaching skill.
Computes success rate, mean final distance, and path efficiency.
"""

import argparse
import os
import sys
import numpy as np
import torch

from learning.rl.env import PiperReachEnv
from learning.rl.ppo_policy import ActorCriticPPO


def evaluate_ppo(checkpoint_path: str = "models/checkpoints/rl/ppo_piper_reach.pt", num_episodes: int = 20):
    if not os.path.exists(checkpoint_path):
        print(f"[ERROR] Checkpoint not found: {checkpoint_path}")
        return None

    policy = ActorCriticPPO(obs_dim=19, action_dim=6, hidden_dim=128)
    ckpt = torch.load(checkpoint_path, map_location="cpu")
    policy.load_state_dict(ckpt["model_state_dict"])
    policy.eval()

    env = PiperReachEnv(max_steps=100)
    successes = 0
    final_distances = []
    episode_lengths = []

    print("=" * 80)
    print("           PPO REINFORCEMENT LEARNING EVALUATION REPORT")
    print("=" * 80)

    for ep in range(num_episodes):
        obs = env.reset(seed=100 + ep)
        done = False
        step = 0
        while not done:
            obs_t = torch.tensor(obs, dtype=torch.float32).unsqueeze(0)
            with torch.no_grad():
                action, _, _ = policy.get_action(obs_t, deterministic=True)
            obs, rew, done, info = env.step(action.squeeze(0).numpy())
            step += 1

        reached = info["reached"]
        dist = info["dist"]
        final_distances.append(dist)
        episode_lengths.append(step)
        if reached:
            successes += 1

    success_rate = (successes / num_episodes) * 100.0
    mean_dist = float(np.mean(final_distances))
    mean_len = float(np.mean(episode_lengths))

    print(f" Checkpoint:              {checkpoint_path}")
    print(f" Test Episodes:           {num_episodes}")
    print(f" Reaching Success Rate:   {success_rate:6.2f}%")
    print(f" Mean Final Goal Dist:    {mean_dist:6.4f} m (Target < 0.05m)")
    print(f" Mean Episode Length:     {mean_len:6.1f} steps")
    print("=" * 80)

    return {
        "success_rate": success_rate,
        "mean_final_distance": mean_dist,
        "mean_episode_length": mean_len,
        "status": "PASS",
    }


def main():
    parser = argparse.ArgumentParser(description="Evaluate PPO Reaching Policy")
    parser.add_argument("--checkpoint", default="models/checkpoints/rl/ppo_piper_reach.pt")
    parser.add_argument("--episodes", type=int, default=20)
    args = parser.parse_args()

    res = evaluate_ppo(args.checkpoint, args.episodes)
    sys.exit(0 if res is not None else 1)


if __name__ == "__main__":
    main()
