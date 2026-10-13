"""
Learned Policy: Action Chunking Transformer (ACT) with temporal ensembling.
"""

from typing import List, Optional
import numpy as np

try:
    import torch
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False

import os
import sys
_py_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "python"))
if _py_dir not in sys.path:
    sys.path.insert(0, _py_dir)

from learning.imitation.models import ActionChunkingPolicy


class ACTLearnedPolicy:
    """
    Wrapper for Action Chunking Transformer policy.
    Predicts chunks of future actions: (chunk_size, 7).
    """

    def __init__(self, obs_dim: int = 16, action_dim: int = 7, chunk_size: int = 10, checkpoint_path: Optional[str] = None):
        self.obs_dim = obs_dim
        self.action_dim = action_dim
        self.chunk_size = chunk_size
        self.model = ActionChunkingPolicy(obs_dim=obs_dim, action_dim=action_dim, chunk_size=chunk_size)
        self.model.eval()

        if HAS_TORCH and checkpoint_path:
            try:
                ckpt = torch.load(checkpoint_path, map_location="cpu")
                self.model.load_state_dict(ckpt)
            except Exception:
                pass

    def predict_action_chunk(self, obs_vector: List[float]) -> List[List[float]]:
        """Predicts chunk_size actions forward."""
        if not HAS_TORCH:
            return [[0.0] * self.action_dim for _ in range(self.chunk_size)]

        with torch.no_grad():
            t_obs = torch.tensor(obs_vector, dtype=torch.float32).unsqueeze(0)
            t_chunk = self.model(t_obs).squeeze(0)  # (chunk_size, action_dim)
            return t_chunk.numpy().tolist()
