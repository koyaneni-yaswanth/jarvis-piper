# JARVIS-PiPER Models Directory

This directory stores neural network architectures, pre-trained weights, training checkpoints, and exported models.

---

## Directory Organization

```
models/
├── checkpoints/         # Training epoch checkpoints
│   └── vjepa/
│       ├── vjepa_latest.pt
│       └── vjepa_checkpoint_simulated.json
├── exported/            # Exported deployment models
│   └── vjepa/
│       ├── vjepa_context_encoder.pt   # TorchScript
│       └── vjepa_context_encoder.onnx # ONNX
└── evaluations/         # Benchmarking JSON summaries
    └── vjepa_metrics.json
```

---

## Model Commands

- **Train V-JEPA World Model**:
  ```bash
  jarvis-piper train --config configs/vjepa.yaml --epochs 10 --batch-size 4
  ```
- **Evaluate Representations**:
  ```bash
  jarvis-piper evaluate --config configs/evaluation.yaml
  ```
- **Export Checkpoints**:
  ```bash
  python3 python/world_model/vjepa/export.py --format torchscript
  ```
