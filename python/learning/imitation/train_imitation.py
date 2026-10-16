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

# Ensure repo python/ directory is in sys.path
_repo_python = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _repo_python not in sys.path:
    sys.path.insert(0, _repo_python)

from learning.imitation.models import BehavioralCloningPolicy, ActionChunkingPolicy


def load_demonstration_episodes(data_dir: str):
    """Loads recorded episodes (from HDF5 or JSON) preserving episode boundaries."""
    episodes = []

    # 1. Check for HDF5 demonstration files
    h5_files = []
    if os.path.isfile(data_dir) and (data_dir.endswith(".hdf5") or data_dir.endswith(".h5")):
        h5_files = [data_dir]
    elif os.path.isdir(data_dir):
        h5_files = sorted(glob.glob(os.path.join(data_dir, "*.hdf5")) + glob.glob(os.path.join(data_dir, "*.h5")))

    if h5_files:
        import h5py
        print(f"[INFO] Discovered {len(h5_files)} HDF5 demonstration file(s) in {data_dir}")
        for h5_p in h5_files:
            try:
                with h5py.File(h5_p, "r") as f:
                    if "observations/qpos" in f and "action" in f:
                        qpos = f["observations/qpos"][:]
                        act = f["action"][:]
                        if len(qpos) < 50:
                            print(f"[INFO] Skipping {os.path.basename(h5_p)}: Insufficient frames ({len(qpos)} < 50)")
                            continue
                        episodes.append({
                            "episode_id": os.path.splitext(os.path.basename(h5_p))[0],
                            "obs": torch.tensor(qpos, dtype=torch.float32),
                            "act": torch.tensor(act, dtype=torch.float32),
                        })
            except Exception as e:
                print(f"[WARN] Error reading HDF5 {h5_p}: {e}")

    # 2. Check for JSON trajectory directories
    if not episodes and os.path.isdir(data_dir):
        ep_dirs = sorted(glob.glob(os.path.join(data_dir, "ep_*")))
        for ep_p in ep_dirs:
            traj_p = os.path.join(ep_p, "trajectory.json")
            if not os.path.exists(traj_p):
                continue
            with open(traj_p, "r", encoding="utf-8") as f:
                data = json.load(f)
            steps = data.get("timesteps", [])
            ep_obs = []
            ep_act = []
            for s in steps:
                q = s.get("joint_positions", [0.0] * 6)[:6]
                v = s.get("joint_velocities", [0.0] * 6)[:6]
                tcp_pos = s.get("tcp_pose", {}).get("position", [0.35, 0.0, 0.25])[:3]
                stroke = s.get("gripper_stroke", 0.035)

                obs = q + v + tcp_pos + [stroke]
                act = s.get("action", q)[:6] + [stroke, 1.0]

                ep_obs.append(obs)
                ep_act.append(act)

            if len(ep_obs) >= 50:
                episodes.append({
                    "episode_id": os.path.basename(ep_p),
                    "obs": torch.tensor(ep_obs, dtype=torch.float32),
                    "act": torch.tensor(ep_act, dtype=torch.float32),
                })

    if not episodes:
        print("[INFO] No existing episodes found. Generating synthetic demonstration buffer...")
        for ep in range(4):
            ep_obs = []
            ep_act = []
            for t in range(50):
                tau = t * 0.02
                q = [0.2 * np.sin(tau), 0.5 + 0.1 * np.cos(tau), -0.6, 0.1, 0.0, 0.0]
                v = [0.2 * np.cos(tau), -0.1 * np.sin(tau), 0.0, 0.0, 0.0, 0.0]
                tcp = [0.35, 0.1 * np.sin(tau), 0.25]
                stroke = 0.035 if t < 25 else 0.010
                obs = q + v + tcp + [stroke]
                act = q + [stroke, 1.0]
                ep_obs.append(obs)
                ep_act.append(act)
            episodes.append({
                "episode_id": f"synthetic_ep_{ep:02d}",
                "obs": torch.tensor(ep_obs, dtype=torch.float32),
                "act": torch.tensor(ep_act, dtype=torch.float32),
            })

    return episodes


def load_demonstration_tensors(data_dir: str):
    """Loads all demonstration frames as concatenated tensors (legacy interface)."""
    episodes = load_demonstration_episodes(data_dir)
    all_obs = torch.cat([ep["obs"] for ep in episodes], dim=0)
    all_acts = torch.cat([ep["act"] for ep in episodes], dim=0)
    return all_obs, all_acts


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

    episodes = load_demonstration_episodes(data_dir)
    n_ep = len(episodes)
    print(f"Discovered {n_ep} demonstration episode(s). Splitting by episode to prevent frame leakage...")

    # Episode-level split: 70% train, 15% val, 15% test
    n_test = max(1, int(n_ep * 0.15)) if n_ep >= 5 else 0
    n_val = max(1, int(n_ep * 0.15)) if n_ep >= 4 else (1 if n_ep >= 2 else 0)
    n_train = max(1, n_ep - n_val - n_test)

    train_eps = episodes[:n_train]
    val_eps = episodes[n_train:n_train + n_val] if n_val > 0 else []
    test_eps = episodes[n_train + n_val:] if n_test > 0 else []

    split_manifest = {
        "train_episodes": [ep["episode_id"] for ep in train_eps],
        "val_episodes": [ep["episode_id"] for ep in val_eps],
        "test_episodes": [ep["episode_id"] for ep in test_eps],
    }
    print(f" Split summary: {len(train_eps)} Train, {len(val_eps)} Val, {len(test_eps)} Test episodes")

    train_obs = torch.cat([ep["obs"] for ep in train_eps], dim=0)
    train_act = torch.cat([ep["act"] for ep in train_eps], dim=0)
    print(f" Train steps: {len(train_obs)} | Obs dim: {train_obs.shape[1]} | Action dim: {train_act.shape[1]}")

    # Compute normalization statistics ONLY on training set (preventing data leakage)
    mean_obs = train_obs.mean(dim=0)
    std_obs = train_obs.std(dim=0)
    std_obs[std_obs < 1e-6] = 1.0

    train_dataset = TensorDataset(train_obs, train_act)
    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)

    val_loader = None
    if val_eps:
        val_obs = torch.cat([ep["obs"] for ep in val_eps], dim=0)
        val_act = torch.cat([ep["act"] for ep in val_eps], dim=0)
        val_dataset = TensorDataset(val_obs, val_act)
        val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False)

    obs_dim = int(train_obs.shape[1])
    action_dim = int(train_act.shape[1])

    if model_type.lower() == "act":
        policy = ActionChunkingPolicy(obs_dim=obs_dim, action_dim=action_dim, chunk_size=5).to(device)
    else:
        policy = BehavioralCloningPolicy(obs_dim=obs_dim, action_dim=action_dim, hidden_dim=256, num_layers=4).to(device)

    policy.set_normalization_stats(mean_obs.to(device), std_obs.to(device))

    optimizer = optim.AdamW(policy.parameters(), lr=lr, weight_decay=1e-4)
    scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs)
    loss_fn = nn.MSELoss()

    start_time = time.time()
    train_history = []
    val_history = []

    print("\n--- Starting Imitation Learning Training ---")
    for epoch in range(1, epochs + 1):
        policy.train()
        epoch_loss = 0.0
        batches = 0

        for batch_obs, batch_act in train_loader:
            batch_obs = batch_obs.to(device)
            batch_act = batch_act.to(device)

            optimizer.zero_grad()
            pred_act = policy(batch_obs)

            if model_type.lower() == "act":
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
        avg_train_loss = epoch_loss / max(1, batches)
        train_history.append(avg_train_loss)

        # Validation pass
        avg_val_loss = None
        if val_loader:
            policy.eval()
            val_loss_sum = 0.0
            val_batches = 0
            with torch.no_grad():
                for v_obs, v_act in val_loader:
                    v_obs = v_obs.to(device)
                    v_act = v_act.to(device)
                    v_pred = policy(v_obs)
                    if model_type.lower() == "act":
                        v_target = v_act.unsqueeze(1).repeat(1, 5, 1)
                        l = loss_fn(v_pred, v_target)
                    else:
                        l = loss_fn(v_pred, v_act)
                    val_loss_sum += l.item()
                    val_batches += 1
            avg_val_loss = val_loss_sum / max(1, val_batches)
            val_history.append(avg_val_loss)

        if epoch % 5 == 0 or epoch == 1 or epoch == epochs:
            val_str = f" | Val MSE: {avg_val_loss:8.6f}" if avg_val_loss is not None else ""
            print(f" Epoch [{epoch:2d}/{epochs:2d}] - Train MSE: {avg_train_loss:8.6f}{val_str} - LR: {scheduler.get_last_lr()[0]:.6f}")

    elapsed = time.time() - start_time
    print(f"--- Training Finished in {elapsed:.2f}s ---")

    # Offline evaluation on held-out test episodes
    test_metrics = {}
    if test_eps:
        policy.eval()
        test_obs = torch.cat([ep["obs"] for ep in test_eps], dim=0).to(device)
        test_act = torch.cat([ep["act"] for ep in test_eps], dim=0).to(device)
        with torch.no_grad():
            test_preds = policy(test_obs)
            if model_type.lower() == "act":
                test_preds = test_preds[:, 0, :]
        test_err = (test_preds - test_act).cpu().numpy()
        test_metrics = {
            "test_steps": len(test_obs),
            "test_mse": float(np.mean(test_err ** 2)),
            "test_mae": float(np.mean(np.abs(test_err))),
            "test_max_err": float(np.max(np.abs(test_err))),
        }
        print(f"\n Held-Out Test Evaluation ({len(test_eps)} episodes, {len(test_obs)} steps):")
        print(f"   Test MSE: {test_metrics['test_mse']:.6f}")
        print(f"   Test MAE: {test_metrics['test_mae']:.6f}")
        print(f"   Test Max Error: {test_metrics['test_max_err']:.6f}")

    # Save Checkpoint
    checkpoint_path = os.path.join(output_dir, f"{model_type}_piper_policy.pt")
    torch.save({
        "epoch": epochs,
        "model_state_dict": policy.state_dict(),
        "obs_mean": mean_obs,
        "obs_std": std_obs,
        "train_loss_history": train_history,
        "val_loss_history": val_history,
        "final_train_loss": train_history[-1],
        "final_val_loss": val_history[-1] if val_history else None,
        "test_metrics": test_metrics,
        "splits": split_manifest,
        "model_type": model_type,
        "obs_dim": obs_dim,
        "action_dim": action_dim,
        "training_duration_s": elapsed,
    }, checkpoint_path)

    # Save machine-readable manifest
    manifest = {
        "model_id": f"{model_type}_piper_v1",
        "checkpoint_path": checkpoint_path,
        "model_type": model_type,
        "epochs": epochs,
        "final_train_mse_loss": float(train_history[-1]),
        "final_val_mse_loss": float(val_history[-1]) if val_history else None,
        "test_metrics": test_metrics,
        "splits": split_manifest,
        "device": str(device),
        "obs_dim": obs_dim,
        "action_dim": action_dim,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    with open(os.path.join(output_dir, f"{model_type}_manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    print(f"[SUCCESS] Checkpoint saved: {checkpoint_path}")
    return checkpoint_path, train_history[-1]


def main():
    parser = argparse.ArgumentParser(description="Train Imitation Learning Policy")
    parser.add_argument("--data-dir", default="dataset/raw", help="Path to raw dataset")
    parser.add_argument("--output-dir", default="models/checkpoints/imitation", help="Checkpoint output folder")
    parser.add_argument("--epochs", type=int, default=20, help="Training epochs")
    parser.add_argument("--batch-size", type=int, default=32, help="Batch size for training")
    parser.add_argument("--model-type", choices=["bc", "act"], default="bc", help="Policy architecture")
    args = parser.parse_args()

    train_policy(
        data_dir=args.data_dir,
        output_dir=args.output_dir,
        epochs=args.epochs,
        batch_size=args.batch_size,
        model_type=args.model_type,
    )


if __name__ == "__main__":
    main()
