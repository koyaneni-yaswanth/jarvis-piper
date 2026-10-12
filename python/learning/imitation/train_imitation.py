#!/usr/bin/env python3
"""
Reproducible Imitation Learning Training Pipeline for AgileX PiPER.
Trains Behavioral Cloning (BC) or Action Chunking (ACT) policy on demonstration dataset.
"""

import argparse
import glob
import json
import os
import sys
import time
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset

from learning.imitation.models import BehavioralCloningPolicy, ActionChunkingPolicy


def load_demonstration_tensors(data_dir: str):
    """Loads recorded episodes and extracts (obs, action) tensor pairs."""
    ep_dirs = sorted(glob.glob(os.path.join(data_dir, "ep_*")))
    all_obs = []
    all_acts = []

    for ep_p in ep_dirs:
        traj_p = os.path.join(ep_p, "trajectory.json")
        if not os.path.exists(traj_p):
            continue
        with open(traj_p, "r", encoding="utf-8") as f:
            data = json.load(f)
        steps = data.get("timesteps", [])
        for s in steps:
            q = s.get("joint_positions", [0.0] * 6)[:6]
            v = s.get("joint_velocities", [0.0] * 6)[:6]
            tcp_pos = s.get("tcp_pose", {}).get("position", [0.35, 0.0, 0.25])[:3]
            stroke = s.get("gripper_stroke", 0.035)

            obs = q + v + tcp_pos + [stroke]
            act = s.get("action", q)[:6] + [stroke, 1.0]

            all_obs.append(obs)
            all_acts.append(act)

    if not all_obs:
        print("[INFO] No existing episodes found. Generating synthetic demonstration buffer...")
        # Synthetic fallback demonstrations for testing/training validation
        for ep in range(4):
            for t in range(50):
                tau = t * 0.02
                q = [0.2 * np.sin(tau), 0.5 + 0.1 * np.cos(tau), -0.6, 0.1, 0.0, 0.0]
                v = [0.2 * np.cos(tau), -0.1 * np.sin(tau), 0.0, 0.0, 0.0, 0.0]
                tcp = [0.35, 0.1 * np.sin(tau), 0.25]
                stroke = 0.035 if t < 25 else 0.010
                obs = q + v + tcp + [stroke]
                act = q + [stroke, 1.0]
                all_obs.append(obs)
                all_acts.append(act)

    obs_tensor = torch.tensor(all_obs, dtype=torch.float32)
    act_tensor = torch.tensor(all_acts, dtype=torch.float32)
    return obs_tensor, act_tensor


def train_policy(
    data_dir: str = "dataset/raw",
    output_dir: str = "models/checkpoints/imitation",
    epochs: int = 20,
    batch_size: int = 32,
    lr: float = 1e-3,
    model_type: str = "bc",
):
    os.makedirs(output_dir, exist_ok=True)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Training Device: {device} | Model Type: {model_type.upper()}")

    obs_tensor, act_tensor = load_demonstration_tensors(data_dir)
    print(f"Loaded {len(obs_tensor)} demonstration steps (Obs dim: {obs_tensor.shape[1]}, Action dim: {act_tensor.shape[1]})")

    # Compute normalization statistics
    mean_obs = obs_tensor.mean(dim=0)
    std_obs = obs_tensor.std(dim=0)

    dataset = TensorDataset(obs_tensor, act_tensor)
    loader = DataLoader(dataset, batch_size=batch_size, shuffle=True)

    if model_type.lower() == "act":
        policy = ActionChunkingPolicy(obs_dim=16, action_dim=8, chunk_size=5).to(device)
    else:
        policy = BehavioralCloningPolicy(obs_dim=16, action_dim=8, hidden_dim=256, num_layers=4).to(device)

    policy.set_normalization_stats(mean_obs.to(device), std_obs.to(device))

    optimizer = optim.AdamW(policy.parameters(), lr=lr, weight_decay=1e-4)
    scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs)
    loss_fn = nn.MSELoss()

    start_time = time.time()
    history = []

    print("\n--- Starting Imitation Learning Training ---")
    for epoch in range(1, epochs + 1):
        policy.train()
        epoch_loss = 0.0
        batches = 0

        for batch_obs, batch_act in loader:
            batch_obs = batch_obs.to(device)
            batch_act = batch_act.to(device)

            optimizer.zero_grad()
            pred_act = policy(batch_obs)

            if model_type.lower() == "act":
                # Compare against expanded chunk
                target_chunk = batch_act.unsqueeze(1).repeat(1, 5, 1)
                loss = loss_fn(pred_act, target_chunk)
            else:
                loss = loss_fn(pred_act, batch_act)

            loss.backward()
            torch.nn.utils.clip_grad_norm_(policy.parameters(), max_norm=1.0)
            optimizer.step()

            epoch_loss += loss.item()
            batches += 1

        scheduler.step()
        avg_loss = epoch_loss / max(1, batches)
        history.append(avg_loss)
        if epoch % 5 == 0 or epoch == 1 or epoch == epochs:
            print(f" Epoch [{epoch:2d}/{epochs:2d}] - MSE Loss: {avg_loss:8.6f} - LR: {scheduler.get_last_lr()[0]:.6f}")

    elapsed = time.time() - start_time
    print(f"--- Training Finished in {elapsed:.2f}s ---")

    # Save Checkpoint
    checkpoint_path = os.path.join(output_dir, f"{model_type}_piper_policy.pt")
    torch.save({
        "epoch": epochs,
        "model_state_dict": policy.state_dict(),
        "obs_mean": mean_obs,
        "obs_std": std_obs,
        "loss_history": history,
        "final_loss": history[-1],
        "model_type": model_type,
        "training_duration_s": elapsed,
    }, checkpoint_path)

    # Save machine-readable manifest
    manifest = {
        "model_id": f"{model_type}_piper_v1",
        "checkpoint_path": checkpoint_path,
        "model_type": model_type,
        "epochs": epochs,
        "final_mse_loss": float(history[-1]),
        "device": str(device),
        "obs_dim": 16,
        "action_dim": 8,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    with open(os.path.join(output_dir, f"{model_type}_manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    print(f"[SUCCESS] Checkpoint saved: {checkpoint_path}")
    return checkpoint_path, history[-1]


def main():
    parser = argparse.ArgumentParser(description="Train Imitation Learning Policy")
    parser.add_argument("--data-dir", default="dataset/raw", help="Path to raw dataset")
    parser.add_argument("--output-dir", default="models/checkpoints/imitation", help="Checkpoint output folder")
    parser.add_argument("--epochs", type=int, default=20, help="Training epochs")
    parser.add_argument("--model-type", choices=["bc", "act"], default="bc", help="Policy architecture")
    args = parser.parse_args()

    train_policy(
        data_dir=args.data_dir,
        output_dir=args.output_dir,
        epochs=args.epochs,
        model_type=args.model_type,
    )


if __name__ == "__main__":
    main()
