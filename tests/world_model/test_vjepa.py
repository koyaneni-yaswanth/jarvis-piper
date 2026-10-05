"""
Unit tests for V-JEPA world model components.
"""

import numpy as np
import pytest
from world_model.vjepa.config import VJEPAConfig
from world_model.vjepa.dataset import SpatioTemporalMaskGenerator, VJEPADataset
from world_model.vjepa.model import VJEPAModel
from world_model.vjepa.losses import VJEPALoss
from world_model.vjepa.train import train_vjepa
from world_model.vjepa.visualize import visualize_latent_trajectory


def test_vjepa_config_defaults():
    cfg = VJEPAConfig()
    assert cfg.patch_size == 16
    assert cfg.clip_length == 16
    assert cfg.embed_dim == 256
    assert cfg.ema_decay == 0.996


def test_mask_generator():
    mask_gen = SpatioTemporalMaskGenerator(
        grid_size=(4, 7, 7),
        spatial_mask_ratio=0.5,
    )
    ctx, tgt = mask_gen.generate_mask()
    assert len(ctx) + len(tgt) == 4 * 7 * 7
    # Context and target indices should not overlap
    assert len(np.intersect1d(ctx, tgt)) == 0


def test_vjepa_loss():
    loss_fn = VJEPALoss(loss_type="l1")
    p = np.array([[1.0, 2.0], [3.0, 4.0]])
    t = np.array([[1.1, 1.9], [3.2, 3.8]])
    loss_val = loss_fn(p, t)
    assert 0.0 < loss_val < 1.0


def test_vjepa_training_smoke(tmp_path):
    cfg = VJEPAConfig(
        dataset_dir=str(tmp_path),
        epochs=1,
        batch_size=1,
        output_dir=str(tmp_path / "checkpoints"),
    )
    ckpt = train_vjepa(cfg)
    assert ckpt.exists()


def test_latent_visualization(tmp_path):
    latents = np.random.randn(20, 32)
    out_png = str(tmp_path / "test_traj.png")
    # Will save or skip depending on matplotlib
    res = visualize_latent_trajectory(latents, output_png=out_png)
