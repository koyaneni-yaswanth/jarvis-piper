"""
Learned Policy: Behavior Cloning (BC) Multi-Layer Perceptron.
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

from learning.imitation.models import BehavioralCloningPolicy


class BCLearnedPolicy:
    """
    Wrapper for Behavioral Cloning Policy inference.
    """

    def __init__(self, obs_dim: int = 16, action_dim: int = 7, checkpoint_path: Optional[str] = None):
        self.obs_dim = obs_dim
        self.action_dim = action_dim
        self.model = BehavioralCloningPolicy(obs_dim=obs_dim, action_dim=action_dim)
        self.model.eval()

        if HAS_TORCH and checkpoint_path:
            try:
                ckpt = torch.load(checkpoint_path, map_location="cpu")
                self.model.load_state_dict(ckpt)
            except Exception:
                pass

    def predict_action(self, obs_vector: List[float]) -> List[float]:
        """Maps low-dim observation to 7-D robot action."""
        if not HAS_TORCH:
            return list(obs_vector[:7])

        with torch.no_grad():
            t_obs = torch.tensor(obs_vector, dtype=torch.float32).unsqueeze(0)
            t_act = self.model(t_obs).squeeze(0)
            return t_act.numpy().tolist()
