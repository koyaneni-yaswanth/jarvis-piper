"""
PPO Actor-Critic Policy Network for Continuous Arm Control.
"""

import math
from typing import Tuple
import torch
import torch.nn as nn
from torch.distributions import Normal


class ActorCriticPPO(nn.Module):
    """Actor-Critic network for continuous action space."""

    def __init__(self, obs_dim: int = 19, action_dim: int = 6, hidden_dim: int = 128):
        super().__init__()
        self.obs_dim = obs_dim
        self.action_dim = action_dim

        # Shared feature representation
        self.actor = nn.Sequential(
            nn.Linear(obs_dim, hidden_dim),
            nn.Tanh(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.Tanh(),
            nn.Linear(hidden_dim, action_dim),
        )
        self.log_std = nn.Parameter(torch.ones(action_dim) * -1.0)

        self.critic = nn.Sequential(
            nn.Linear(obs_dim, hidden_dim),
            nn.Tanh(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.Tanh(),
            nn.Linear(hidden_dim, 1),
        )

    def forward(self, obs: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        action_mean = self.actor(obs)
        value = self.critic(obs)
        return action_mean, value

    def get_action(self, obs: torch.Tensor, deterministic: bool = False) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        action_mean = self.actor(obs)
        value = self.critic(obs)
        std = torch.exp(self.log_std)
        dist = Normal(action_mean, std)

        if deterministic:
            action = action_mean
        else:
            action = dist.sample()

        log_prob = dist.log_prob(action).sum(dim=-1)
        return action, log_prob, value.squeeze(-1)

    def evaluate_actions(self, obs: torch.Tensor, actions: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        action_mean = self.actor(obs)
        value = self.critic(obs)
        std = torch.exp(self.log_std)
        dist = Normal(action_mean, std)

        log_prob = dist.log_prob(actions).sum(dim=-1)
        entropy = dist.entropy().sum(dim=-1)
        return log_prob, value.squeeze(-1), entropy
