"""
Unit tests for Behavioral Cloning (BC) and Action Chunking (ACT) policy networks.
"""

import torch
import pytest
from learning.imitation.models import BehavioralCloningPolicy, ActionChunkingPolicy


def test_bc_policy_forward():
    policy = BehavioralCloningPolicy(obs_dim=16, action_dim=8, hidden_dim=64, num_layers=2)
    dummy_obs = torch.randn(4, 16)
    action = policy(dummy_obs)
    assert action.shape == (4, 8)
    assert not torch.isnan(action).any()


def test_act_chunking_policy_forward():
    policy = ActionChunkingPolicy(obs_dim=16, action_dim=8, chunk_size=5, hidden_dim=64)
    dummy_obs = torch.randn(4, 16)
    chunk = policy(dummy_obs)
    assert chunk.shape == (4, 5, 8)
    assert not torch.isnan(chunk).any()
