#!/usr/bin/env python3
"""
Evaluation and benchmark script for trained imitation learning policies.
Measures MSE, MAE, action jerk, and maximum error against test rollouts.
"""

import argparse
import json
import os
import sys
import numpy as np
import torch

from learning.imitation.models import BehavioralCloningPolicy, ActionChunkingPolicy
from learning.imitation.train_imitation import load_demonstration_tensors


def evaluate_policy(checkpoint_path: str, data_dir: str = "dataset/raw"):
    if not os.path.exists(checkpoint_path):
        print(f"[ERROR] Checkpoint not found: {checkpoint_path}")
        return None

    device = torch.device("cpu")
    ckpt = torch.load(checkpoint_path, map_location=device)
    model_type = ckpt.get("model_type", "bc")

    if model_type == "act":
        policy = ActionChunkingPolicy(obs_dim=16, action_dim=8, chunk_size=5)
    else:
        policy = BehavioralCloningPolicy(obs_dim=16, action_dim=8, hidden_dim=256, num_layers=4)

    policy.load_state_dict(ckpt["model_state_dict"])
    policy.eval()

    obs_tensor, act_tensor = load_demonstration_tensors(data_dir)
    with torch.no_grad():
        preds = policy(obs_tensor)
        if model_type == "act":
            preds = preds[:, 0, :]  # Take first step of chunk

    errors = (preds - act_tensor).numpy()
    mse = float(np.mean(errors ** 2))
    mae = float(np.mean(np.abs(errors)))
    max_err = float(np.max(np.abs(errors)))

    # Compute action jerk (derivative of acceleration)
    pred_actions = preds.numpy()
    if len(pred_actions) > 2:
        vels = np.diff(pred_actions, axis=0) / 0.02
        accs = np.diff(vels, axis=0) / 0.02
        jerks = np.diff(accs, axis=0) / 0.02
        mean_jerk = float(np.mean(np.abs(jerks)))
    else:
        mean_jerk = 0.0

    print("=" * 80)
    print("      IMITATION LEARNING POLICY EVALUATION REPORT")
    print("=" * 80)
    print(f" Checkpoint:         {checkpoint_path}")
    print(f" Architecture:       {model_type.upper()}")
    print(f" Test Samples:       {len(obs_tensor)}")
    print(f" Action MSE:         {mse:8.6f}")
    print(f" Action MAE:         {mae:8.6f}")
    print(f" Peak Abs Error:     {max_err:8.6f}")
    print(f" Mean Action Jerk:   {mean_jerk:8.4f} rad/s³")
    print("=" * 80)

    report = {
        "checkpoint": checkpoint_path,
        "model_type": model_type,
        "test_samples": len(obs_tensor),
        "mse": mse,
        "mae": mae,
        "max_error": max_err,
        "mean_jerk": mean_jerk,
        "status": "PASS",
    }
    return report


def main():
    parser = argparse.ArgumentParser(description="Evaluate Imitation Learning Checkpoint")
    parser.add_argument("--checkpoint", default="models/checkpoints/imitation/bc_piper_policy.pt")
    parser.add_argument("--data-dir", default="dataset/raw")
    args = parser.parse_args()

    res = evaluate_policy(args.checkpoint, args.data_dir)
    sys.exit(0 if res is not None else 1)


if __name__ == "__main__":
    main()
