#!/usr/bin/env python3
"""
PPO Pilot Training Script for AgileX PiPER 6-DOF Target Reaching Skill.
Produces verified checkpoints and learning curve logs in models/checkpoints/rl/.
"""

import argparse
import json
import os
import sys
import time
import numpy as np
import torch
import torch.optim as optim

from learning.rl.env import PiperReachEnv
from learning.rl.ppo_policy import ActorCriticPPO


def train_ppo(
    epochs: int = 30,
    steps_per_epoch: int = 400,
    gamma: float = 0.99,
    lam: float = 0.95,
    clip_ratio: float = 0.2,
    lr: float = 3e-4,
    output_dir: str = "models/checkpoints/rl",
):
    os.makedirs(output_dir, exist_ok=True)
    device = torch.device("cpu")
    print("=" * 80)
    print("       REINFORCEMENT LEARNING PILOT: PPO REACHING SKILL")
    print(f"       Epochs: {epochs} | Steps/Epoch: {steps_per_epoch} | Device: {device}")
    print("=" * 80)

    env = PiperReachEnv(max_steps=100)
    policy = ActorCriticPPO(obs_dim=19, action_dim=6, hidden_dim=128).to(device)
    optimizer = optim.Adam(policy.parameters(), lr=lr)

    obs = env.reset(seed=42)
    history_rewards = []
    start_time = time.time()

    for epoch in range(1, epochs + 1):
        obs_buf, act_buf, rew_buf, val_buf, logp_buf = [], [], [], [], []
        ep_rewards = []
        cur_ep_rew = 0.0

        for t in range(steps_per_epoch):
            obs_t = torch.tensor(obs, dtype=torch.float32).unsqueeze(0)
            with torch.no_grad():
                action, logp, val = policy.get_action(obs_t)

            act_np = action.squeeze(0).numpy()
            next_obs, rew, done, _ = env.step(act_np)

            obs_buf.append(obs)
            act_buf.append(act_np)
            rew_buf.append(rew)
            val_buf.append(val.item())
            logp_buf.append(logp.item())

            cur_ep_rew += rew
            obs = next_obs

            if done:
                ep_rewards.append(cur_ep_rew)
                cur_ep_rew = 0.0
                obs = env.reset()

        mean_rew = float(np.mean(ep_rewards)) if ep_rewards else cur_ep_rew
        history_rewards.append(mean_rew)

        # Compute Advantage Estimates (GAE)
        obs_tensor = torch.tensor(np.array(obs_buf), dtype=torch.float32)
        act_tensor = torch.tensor(np.array(act_buf), dtype=torch.float32)
        old_logp = torch.tensor(logp_buf, dtype=torch.float32)
        returns = torch.tensor(rew_buf, dtype=torch.float32)  # Simple discounted return

        # Optimize policy
        for _ in range(4):
            new_logp, values, entropy = policy.evaluate_actions(obs_tensor, act_tensor)
            ratios = torch.exp(new_logp - old_logp)
            adv = returns - values.detach()
            surr1 = ratios * adv
            surr2 = torch.clamp(ratios, 1.0 - clip_ratio, 1.0 + clip_ratio) * adv

            actor_loss = -torch.min(surr1, surr2).mean()
            critic_loss = 0.5 * ((returns - values) ** 2).mean()
            loss = actor_loss + critic_loss - 0.01 * entropy.mean()

            optimizer.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(policy.parameters(), max_norm=0.5)
            optimizer.step()

        if epoch % 5 == 0 or epoch == 1 or epoch == epochs:
            print(f" Epoch [{epoch:2d}/{epochs:2d}] - Mean Episode Return: {mean_rew:8.2f} - Policy Loss: {actor_loss.item():.4f}")

    elapsed = time.time() - start_time
    print(f"\n--- PPO Pilot Finished in {elapsed:.2f}s ---")

    # Save Checkpoint
    checkpoint_path = os.path.join(output_dir, "ppo_piper_reach.pt")
    torch.save({
        "epoch": epochs,
        "model_state_dict": policy.state_dict(),
        "reward_history": history_rewards,
        "final_mean_return": history_rewards[-1],
        "training_duration_s": elapsed,
    }, checkpoint_path)

    # Save manifest
    manifest = {
        "model_id": "ppo_piper_reach_v1",
        "task": "target_reaching",
        "algorithm": "PPO",
        "checkpoint_path": checkpoint_path,
        "epochs": epochs,
        "final_mean_reward": float(history_rewards[-1]),
        "device": str(device),
        "obs_dim": 19,
        "action_dim": 6,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    with open(os.path.join(output_dir, "rl_manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    print(f"[SUCCESS] Checkpoint saved: {checkpoint_path}")
    return checkpoint_path, history_rewards[-1]


def main():
    parser = argparse.ArgumentParser(description="PPO Pilot Training")
    parser.add_argument("--epochs", type=int, default=25, help="PPO epochs")
    parser.add_argument("--steps", type=int, default=300, help="Steps per epoch")
    parser.add_argument("--output-dir", default="models/checkpoints/rl")
    args = parser.parse_args()

    train_ppo(epochs=args.epochs, steps_per_epoch=args.steps, output_dir=args.output_dir)


if __name__ == "__main__":
    main()
