"""
Layer B: Imitation Learning Policy Architectures (BC & ACT Chunking).
"""

import math
from typing import Dict, Optional, Tuple
import torch
import torch.nn as nn
import torch.nn.functional as F


class BehavioralCloningPolicy(nn.Module):
    """
    MLP / Residual Behavioral Cloning Policy mapping 16-D state observation
    (joint_positions, velocities, TCP position, gripper) to 8-D action target.
    """

    def __init__(
        self,
        obs_dim: int = 16,
        action_dim: int = 8,
        hidden_dim: int = 256,
        num_layers: int = 4,
        dropout: float = 0.05,
    ):
        super().__init__()
        self.obs_dim = obs_dim
        self.action_dim = action_dim

        # Running observation normalizer buffers
        self.register_buffer("obs_mean", torch.zeros(obs_dim))
        self.register_buffer("obs_std", torch.ones(obs_dim))

        layers = []
        in_d = obs_dim
        for _ in range(num_layers):
            layers.append(nn.Linear(in_d, hidden_dim))
            layers.append(nn.LayerNorm(hidden_dim))
            layers.append(nn.GELU())
            layers.append(nn.Dropout(dropout))
            in_d = hidden_dim

        self.backbone = nn.Sequential(*layers)
        self.action_head = nn.Linear(hidden_dim, action_dim)

    def set_normalization_stats(self, mean: torch.Tensor, std: torch.Tensor):
        self.obs_mean.copy_(mean)
        self.obs_std.copy_(torch.clamp(std, min=1e-4))

    def normalize_obs(self, obs: torch.Tensor) -> torch.Tensor:
        return (obs - self.obs_mean) / self.obs_std

    def forward(self, obs: torch.Tensor) -> torch.Tensor:
        obs_norm = self.normalize_obs(obs)
        feat = self.backbone(obs_norm)
        action = self.action_head(feat)
        return action


class ActionChunkingPolicy(nn.Module):
    """
    Action Chunking with Transformers (ACT) style policy predicting
    a temporal horizon chunk of future actions (k_chunk, action_dim).
    """

    def __init__(
        self,
        obs_dim: int = 16,
        action_dim: int = 8,
        chunk_size: int = 10,
        hidden_dim: int = 256,
    ):
        super().__init__()
        self.obs_dim = obs_dim
        self.action_dim = action_dim
        self.chunk_size = chunk_size

        self.register_buffer("obs_mean", torch.zeros(obs_dim))
        self.register_buffer("obs_std", torch.ones(obs_dim))

        self.encoder = nn.Sequential(
            nn.Linear(obs_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.ReLU(),
        )
        self.chunk_head = nn.Linear(hidden_dim, chunk_size * action_dim)

    def set_normalization_stats(self, mean: torch.Tensor, std: torch.Tensor):
        self.obs_mean.copy_(mean)
        self.obs_std.copy_(torch.clamp(std, min=1e-4))

    def forward(self, obs: torch.Tensor) -> torch.Tensor:
        obs_norm = (obs - self.obs_mean) / self.obs_std
        feat = self.encoder(obs_norm)
        chunk = self.chunk_head(feat)
        batch_size = obs.shape[0]
        return chunk.view(batch_size, self.chunk_size, self.action_dim)
