"""
Module C: Action-Conditioned World Model (V-JEPA 2-AC Adapter).
Bridges Piper 6-DOF joint actions and gripper stroke into V-JEPA latent conditioning tokens.
Provides multi-step forward predictive rollouts in latent space:
z_{t+k} = Predictor(z_t, a_{t:t+k})
"""

from typing import Dict, Any, List, Tuple, Optional
import numpy as np

try:
    import torch
    import torch.nn as nn
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False

import os
import sys
_py_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "python"))
if _py_dir not in sys.path:
    sys.path.insert(0, _py_dir)

from world_model.vjepa.config import VJEPAConfig
from world_model.vjepa.model import VJEPAModel


try:
    import cv2
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False


class PiperActionAdapter(nn.Module if HAS_TORCH else object):
    """
    Projects Piper 7-dimensional action vector [q1..q6, stroke]
    into the V-JEPA latent embedding space (embed_dim = 192/768).
    """

    def __init__(self, action_dim: int = 7, embed_dim: int = 192):
        if HAS_TORCH:
            super().__init__()
            self.net = nn.Sequential(
                nn.Linear(action_dim, 64),
                nn.SiLU(),
                nn.Linear(64, embed_dim),
            )
        self.action_dim = action_dim
        self.embed_dim = embed_dim

    def forward(self, actions: Any) -> Any:
        if not HAS_TORCH:
            return None
        return self.net(actions)


class VJEPAActionConditionedModel:
    """
    Action-Conditioned Visual World Model for AgileX PiPER 6-DOF.
    """

    def __init__(self, config: Optional[VJEPAConfig] = None):
        self.config = config or VJEPAConfig()
        self.model = VJEPAModel(self.config)
        self.model.eval_mode()
        self.action_adapter = PiperActionAdapter(action_dim=7, embed_dim=self.config.embed_dim)

    def _normalize_clip(self, clip: np.ndarray) -> np.ndarray:
        if clip.ndim == 4 and clip.shape[-1] == 3:
            v_in = clip
        elif clip.ndim == 4 and clip.shape[1] == 3:
            v_in = np.transpose(clip, (0, 2, 3, 1))
        else:
            v_in = clip

        H_t, W_t = self.config.image_size
        processed = []
        for f in v_in:
            if HAS_CV2:
                f_r = cv2.resize(f, (W_t, H_t))
            else:
                f_r = np.zeros((H_t, W_t, 3), dtype=np.uint8)
            f_norm = (f_r.astype(np.float32) / 127.5) - 1.0
            processed.append(np.transpose(f_norm, (2, 0, 1)))

        while len(processed) < self.config.clip_length:
            processed.append(np.copy(processed[-1]) if processed else np.zeros((3, H_t, W_t), dtype=np.float32))

        return np.stack(processed[:self.config.clip_length], axis=0)

    def rollout_latent_trajectory(
        self,
        initial_frames: np.ndarray,
        candidate_actions: List[List[float]],
    ) -> List[np.ndarray]:
        """
        Rolls out the latent state representation across a multi-step action sequence.
        candidate_actions: List of 7-dim actions [q1..q6, stroke]
        Returns:
            trajectory_latents: List of (D,) feature vectors for each step.
        """
        if not HAS_TORCH:
            return [np.zeros(self.config.embed_dim, dtype=np.float32) for _ in candidate_actions]

        # Prepare normalized video tensor (T, 3, H, W)
        v_norm = self._normalize_clip(initial_frames)

        with torch.no_grad():
            v_t = torch.from_numpy(v_norm).unsqueeze(0).float()
            z_current = self.model.context_encoder(v_t)  # (1, N_tokens, D)
            num_tokens = z_current.shape[1]
            pos_indices = torch.arange(num_tokens).unsqueeze(0)

            latents = []
            for act in candidate_actions:
                act_tensor = torch.tensor(act, dtype=torch.float32).unsqueeze(0)
                # Apply action conditioning through predictor
                z_next = self.model.predictor(z_current, pos_indices, target_indices=pos_indices, robot_state=act_tensor)
                # Mean pool for 1D summary
                z_pooled = z_next.mean(dim=1).squeeze(0).cpu().numpy()
                latents.append(z_pooled)
                z_current = z_next

        return latents

