# V-JEPA Pretraining Guide

This guide details how to train the V-JEPA visual world model on demonstration episodes collected with the AgileX PiPER system.

---

## 1. Preparing the Dataset

Ensure recorded or synthetic demonstrations are placed in `dataset/raw/`:

```bash
# Verify dataset validity and count
jarvis-piper dataset --dataset-dir dataset/raw
jarvis-piper validate --dataset dataset/raw
```

---

## 2. Launching Training

### Via CLI:
```bash
jarvis-piper train --config configs/vjepa.yaml --epochs 10 --batch-size 4
```

### Via Shell Script:
```bash
./scripts/train_vjepa.sh 10
```

### Direct Python Invocation:
```bash
python3 python/world_model/vjepa/train.py --config configs/vjepa.yaml --epochs 10 --batch-size 4 --device cuda
```

---

## 3. Key Hyperparameters (`configs/vjepa.yaml`)

| Parameter | Recommended Default | Description |
|---|---|---|
| `patch_size` | 16 | Spatial patch dimension ($16 \times 16$ pixels) |
| `clip_length` | 16 | Number of frames per temporal video clip |
| `embed_dim` | 256 | Latent feature dimension for ViT encoder |
| `depth` | 4 (Light) / 12 (Base) | Number of transformer layers in context encoder |
| `predictor_depth` | 3 (Light) / 6 (Base) | Number of transformer layers in latent predictor |
| `ema_decay` | 0.996 | Target encoder exponential moving average rate |
| `mask_ratio_spatial` | 0.60 | Ratio of spatial patches masked during pretraining |
| `learning_rate` | $1 \times 10^{-4}$ | Peak AdamW learning rate |
| `weight_decay` | 0.05 | Weight decay regularizer |

Checkpoints are saved automatically to `models/checkpoints/vjepa/`.
