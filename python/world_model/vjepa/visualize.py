"""
V-JEPA Trajectory and Latent Space Visualization.
Projects high-dimensional latent tokens into 2D/3D (via PCA/SVD) and plots predicted vs actual trajectories.
"""

import os
import json
import argparse
import numpy as np
from pathlib import Path
from typing import Optional, Tuple

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    HAS_MPL = True
except ImportError:
    HAS_MPL = False


def visualize_latent_trajectory(
    latents: np.ndarray,
    output_png: str = "experiments/vjepa_latent_trajectory.png",
    title: str = "V-JEPA Latent Space Trajectory",
) -> Optional[str]:
    """
    latents: (T, D) array of temporal latent vectors.
    Projects to 2D using SVD/PCA and saves trajectory plot.
    """
    if latents.ndim > 2:
        latents = latents.reshape(latents.shape[0], -1)

    T, D = latents.shape
    if T < 2:
        return None

    # Center the latents
    centered = latents - np.mean(latents, axis=0, keepdims=True)
    # SVD for 2D projection
    try:
        u, s, vt = np.linalg.svd(centered, full_matrices=False)
        proj = centered @ vt[:2].T  # (T, 2)
    except Exception:
        proj = centered[:, :2]

    if not HAS_MPL:
        print(f"[INFO] Matplotlib not installed; skipping plot generation for {output_png}")
        return None

    Path(output_png).parent.mkdir(parents=True, exist_ok=True)
    plt.figure(figsize=(8, 6))
    plt.plot(proj[:, 0], proj[:, 1], "-o", color="#1f77b4", alpha=0.7, label="Latent Trajectory")
    plt.scatter(proj[0, 0], proj[0, 1], color="green", s=100, label="Start t=0", zorder=5)
    plt.scatter(proj[-1, 0], proj[-1, 1], color="red", s=100, label="End t=T", zorder=5)
    plt.title(title)
    plt.xlabel("Latent Principal Component 1")
    plt.ylabel("Latent Principal Component 2")
    plt.grid(True, linestyle="--", alpha=0.5)
    plt.legend()
    plt.tight_layout()
    plt.savefig(output_png, dpi=150)
    plt.close()

    print(f"[SUCCESS] Latent trajectory visualization saved to {output_png}")
    return output_png


def main():
    parser = argparse.ArgumentParser(description="Visualize V-JEPA latent representations.")
    parser.add_argument("--output", type=str, default="experiments/vjepa_trajectory.png")
    parser.add_argument("--steps", type=int, default=30)
    args = parser.parse_args()

    # Generate synthetic smooth latent trajectory for demo
    t = np.linspace(0, 4 * np.pi, args.steps)
    synth_latents = np.zeros((args.steps, 128))
    synth_latents[:, 0] = np.sin(t)
    synth_latents[:, 1] = np.cos(t)
    synth_latents[:, 2] = t * 0.1

    visualize_latent_trajectory(synth_latents, output_png=args.output)


if __name__ == "__main__":
    main()
