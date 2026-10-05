"""
V-JEPA Training Loop.
Trains the Context Encoder and Latent Predictor with EMA target updates.
Supports standalone execution and CLI invocation.
"""

import os
import sys
import time
import argparse
import json
from pathlib import Path
from typing import Optional

from .config import VJEPAConfig
from .dataset import VJEPADataset
from .model import VJEPAModel
from .losses import VJEPALoss

try:
    import torch
    from torch.utils.data import DataLoader
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False


def train_vjepa(config: VJEPAConfig) -> Path:
    """Runs V-JEPA training given a configuration."""
    output_dir = Path(config.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print(" JARVIS-PiPER :: V-JEPA World Model Training")
    print("=" * 60)
    print(f"Dataset directory : {config.dataset_dir}")
    print(f"Checkpoints dir   : {config.output_dir}")
    print(f"Epochs            : {config.epochs}")
    print(f"Batch size        : {config.batch_size}")
    print(f"PyTorch available : {HAS_TORCH}")
    print("-" * 60)

    dataset = VJEPADataset(config)
    print(f"Discovered episodes: {len(dataset)}")

    model = VJEPAModel(config)
    loss_fn = VJEPALoss(loss_type="l1")

    if not HAS_TORCH:
        print("[WARNING] PyTorch not detected in environment. Running simulated training smoke-test.")
        for epoch in range(1, config.epochs + 1):
            time.sleep(0.1)
            sample = dataset[0]
            loss_val = 0.42 / (epoch + 0.1)
            print(f"Epoch [{epoch}/{config.epochs}] - Simulated Loss: {loss_val:.4f}")
        
        # Save dummy checkpoint
        ckpt_path = output_dir / "vjepa_checkpoint_simulated.json"
        with open(ckpt_path, "w") as f:
            json.dump({
                "status": "simulated_checkpoint",
                "config": config.__dict__,
                "epochs": config.epochs,
            }, f, indent=2)
        print(f"[SUCCESS] Simulated checkpoint written to {ckpt_path}")
        return ckpt_path

    # PyTorch implementation
    device = torch.device("cuda" if torch.cuda.is_available() and config.device != "cpu" else "cpu")
    print(f"Using device: {device}")
    model.to(str(device))
    model.train_mode()

    dataloader = DataLoader(dataset, batch_size=config.batch_size, shuffle=True, drop_last=False)
    
    # Optimize Context Encoder and Latent Predictor parameters
    params = list(model.context_encoder.parameters()) + list(model.predictor.parameters())
    optimizer = torch.optim.AdamW(params, lr=config.learning_rate, weight_decay=config.weight_decay)

    last_ckpt = output_dir / "vjepa_latest.pt"

    for epoch in range(1, config.epochs + 1):
        total_loss = 0.0
        steps = 0
        for batch in dataloader:
            video = batch["video"].to(device)
            ctx_idx = batch["context_indices"].to(device)
            tgt_idx = batch["target_indices"].to(device)
            state = batch["robot_state"].to(device) if config.include_robot_state else None

            optimizer.zero_grad()
            preds, targets = model.forward(video, ctx_idx, tgt_idx, state)
            loss = loss_fn(preds, targets)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(params, max_norm=1.0)
            optimizer.step()

            # EMA target update
            model.update_target_encoder()

            total_loss += loss.item()
            steps += 1

        avg_loss = total_loss / max(1, steps)
        print(f"Epoch [{epoch}/{config.epochs}] - V-JEPA Latent Loss: {avg_loss:.4f}")

        if epoch % config.checkpoint_frequency == 0 or epoch == config.epochs:
            torch.save({
                "epoch": epoch,
                "context_encoder": model.context_encoder.state_dict(),
                "target_encoder": model.target_encoder.state_dict(),
                "predictor": model.predictor.state_dict(),
                "config": config.__dict__,
                "loss": avg_loss,
            }, last_ckpt)
            print(f" -> Checkpoint saved to {last_ckpt}")

    print("=" * 60)
    print(f"[SUCCESS] Training complete. Saved model to: {last_ckpt}")
    print("=" * 60)
    return last_ckpt


def run_training(config_path: str = "configs/vjepa.yaml", epochs: Optional[int] = None, batch_size: Optional[int] = None) -> int:
    """Helper entry point for CLI and script execution."""
    cfg = VJEPAConfig.from_yaml(config_path) if os.path.exists(config_path) else VJEPAConfig()
    if epochs is not None:
        cfg.epochs = epochs
    if batch_size is not None:
        cfg.batch_size = batch_size
    train_vjepa(cfg)
    return 0


def main():
    parser = argparse.ArgumentParser(description="Train V-JEPA World Model on JARVIS-PiPER demonstrations.")
    parser.add_argument("--config", type=str, default="configs/vjepa.yaml", help="Path to vjepa config yaml")
    parser.add_argument("--epochs", type=int, default=None, help="Override number of training epochs")
    parser.add_argument("--batch-size", type=int, default=None, help="Override batch size")
    parser.add_argument("--lr", type=float, default=None, help="Override learning rate")
    parser.add_argument("--output-dir", type=str, default=None, help="Directory to save checkpoints")
    parser.add_argument("--device", type=str, default=None, help="cpu / cuda / auto")
    args = parser.parse_args()

    if os.path.exists(args.config):
        config = VJEPAConfig.from_yaml(args.config)
    else:
        config = VJEPAConfig()

    if args.epochs is not None:
        config.epochs = args.epochs
    if args.batch_size is not None:
        config.batch_size = args.batch_size
    if args.lr is not None:
        config.learning_rate = args.lr
    if args.output_dir is not None:
        config.output_dir = args.output_dir
    if args.device is not None:
        config.device = args.device

    train_vjepa(config)


if __name__ == "__main__":
    main()
