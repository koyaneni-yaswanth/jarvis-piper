# V-JEPA (Video Joint-Embedding Predictive Architecture)

JARVIS-PiPER incorporates a modular implementation of the **Video Joint-Embedding Predictive Architecture (V-JEPA)** tailored for embodied manipulation world modeling.

---

## 1. Motivation: Pixel Reconstruction vs. Latent Space Prediction

Traditional visual world models (e.g. Dreamer, Video Diffusion, Variational Autoencoders) predict future video frames by reconstructing raw pixels. This suffers from:
1. **Perceptual Waste**: High network capacity is wasted modeling visual background noise, shadows, and textures that are irrelevant to manipulation tasks.
2. **Blurry Rollouts**: Pixel losses average multi-modal possibilities, resulting in blurry or unrealistic future predictions.

V-JEPA eliminates pixel decoders entirely. It predicts representations directly in an abstract latent embedding space:

$$\mathcal{L}_{\text{V-JEPA}} = \frac{1}{|M_y|} \sum_{i \in M_y} \|\hat{\mathbf{s}}_{y, i} - \mathbf{s}_{y, i}\|_1$$

where $\hat{\mathbf{s}}_{y, i}$ is the predicted representation of masked patch $i$, and $\mathbf{s}_{y, i}$ is the target representation produced by a target encoder.

---

## 2. Model Architecture

```
                  Video Clip (T=16, H=224, W=224)
                               │
               ┌───────────────┴───────────────┐
               ▼                               ▼
       Context Patches                  Target Patches
      (Unmasked 40-50%)                (Masked 50-60%)
               │                               │
               ▼                               ▼
      Context ViT Encoder             Target ViT Encoder
          (Trainable)                     (EMA-Updated)
               │                               │
               ▼                               ▼
       Context Tokens s_x              Target Tokens s_y
               │                               │
    + Robot Actions a_t                        │
    + Positional Mask Queries                  │
               │                               │
               ▼                               │
        Latent Predictor                       │
               │                               │
               ▼                               │
      Predicted Tokens s^_y                    │
               │                               │
               └───────────► L1 Loss ◄─────────┘
```

### Components:
1. **Context Encoder**: A Vision Transformer (ViT) that operates *only* on the visible, unmasked spatio-temporal video patches.
2. **Target Encoder**: An identical ViT that encodes target video regions to produce ground-truth latent targets. Its parameters are updated via Exponential Moving Average (EMA):
   $$\theta_{\text{target}} \leftarrow \tau \theta_{\text{target}} + (1 - \tau) \theta_{\text{context}}, \quad \tau = 0.996$$
3. **Latent Predictor**: A lightweight transformer conditioned on context representations, query target positions, and robot proprioceptive states/actions.

---

## 3. Configuration & Modularity

The model is configured via `configs/vjepa.yaml` and instantiated in `python/world_model/vjepa/`:
- Multi-GPU & mixed precision training via PyTorch.
- Zero-dependency fallback: runs smoke-test simulation loops if PyTorch is not yet installed on minimal machines.
