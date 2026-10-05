# Evaluation & Quality Benchmarking Guide

JARVIS-PiPER provides tools to evaluate both dataset quality and trained world model representation fidelity.

---

## 1. Dataset Quality Auditing

Before training imitation learning policies or world models, audit the raw recordings:

```bash
jarvis-piper validate --dataset dataset/raw
```

### Validation Checks:
1. **Timestamp Monotonicity**: Checks that $\Delta t = t_{k} - t_{k-1} > 0$ for all frames.
2. **Frequency Jitter**: Verifies standard deviation of loop interval $\sigma(\Delta t) \le 5\text{ ms}$.
3. **Data Completeness**: Ensures zero NaN, Inf, or truncated fields in `trajectory.json`.
4. **Trajectory Smoothness (Jerk)**:
   $$\text{Jerk}_{\text{RMS}} = \sqrt{\frac{1}{N} \sum_{k=1}^N \left\|\frac{d^3 q}{dt^3}\right\|^2}$$
5. **Quality Tier Assignment**:
   - **Tier A**: $\le 0.1\%$ dropped frames, passes all safety envelopes.
   - **Tier B**: $\le 1.0\%$ dropped frames.
   - **Tier C / D**: Flagged for operator review.

---

## 2. World Model Representation Benchmarking

To benchmark a trained V-JEPA checkpoint:

```bash
jarvis-piper evaluate --config configs/evaluation.yaml
```

### Metrics Computed:
- **Mean Latent L1 Error**: Prediction error in latent feature space.
- **Cosine Similarity**: Directional alignment between predicted latent vectors and ground-truth EMA targets.
- **Representation Collapse Audit**: Tracks the standard deviation of features across the test batch; if $\sigma(\mathbf{z}) < 0.05$, a collapse alert is issued.
- **Trajectory Projection**: Projects temporal embeddings via PCA/SVD to generate 2D trajectory visualizations (`experiments/vjepa_latent_trajectory.png`).
