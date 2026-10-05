# JARVIS-PiPER Experiments & Visualizations

This directory stores experiment logs, visual plots, trajectory projections, and benchmark results.

---

## Directory Organization

```
experiments/
├── runs/                         # Training run configs and metrics
├── demo_latent_trajectory.png    # Projected 2D V-JEPA latent space rollout
└── notebook_vjepa_trajectory.png # Latent trajectory generated from Jupyter analysis
```

---

## Visualizing Trajectories

Generate a PCA/SVD projection of high-dimensional latent world model trajectories:

```bash
python3 python/world_model/vjepa/visualize.py --output experiments/my_trajectory.png --steps 60
```
