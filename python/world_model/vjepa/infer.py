"""
V-JEPA Inference and Latent Rollout Engine.
Extracts latent representations and performs predictive rollouts given candidate actions.
"""

import numpy as np
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from .config import VJEPAConfig
from .model import VJEPAModel

try:
    import torch
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False


class VJEPAPredictor:
    """
    High-level API for V-JEPA latent feature extraction and forward trajectory rollouts.
    """

    def __init__(self, config: Optional[VJEPAConfig] = None, checkpoint_path: Optional[str] = None):
        self.config = config or VJEPAConfig()
        self.model = VJEPAModel(self.config)
        self.model.eval_mode()

        if HAS_TORCH and checkpoint_path and Path(checkpoint_path).exists():
            try:
                ckpt = torch.load(checkpoint_path, map_location="cpu")
                if "context_encoder" in ckpt:
                    self.model.context_encoder.load_state_dict(ckpt["context_encoder"])
                if "predictor" in ckpt:
                    self.model.predictor.load_state_dict(ckpt["predictor"])
            except Exception:
                pass

    def encode_context(self, video_frames: np.ndarray) -> np.ndarray:
        """
        Encodes a clip of video frames into context latent tokens.
        video_frames: (T, 3, H, W) or (T, H, W, 3)
        Returns:
            latent_tokens: (N_context, D) feature array
        """
        if video_frames.ndim == 4 and video_frames.shape[-1] == 3:
            video_frames = np.transpose(video_frames, (0, 3, 1, 2))

        if not HAS_TORCH:
            N = (self.config.clip_length // 2) * (self.config.image_size[0] // self.config.patch_size) ** 2
            return np.zeros((N, self.config.embed_dim), dtype=np.float32)

        with torch.no_grad():
            v_t = torch.from_numpy(video_frames).unsqueeze(0).float()
            tokens = self.model.context_encoder(v_t)
            return tokens.squeeze(0).cpu().numpy()

    def rollout_latent(
        self,
        initial_video: np.ndarray,
        future_robot_actions: np.ndarray,
    ) -> np.ndarray:
        """
        Predicts future latent video representations conditioned on robot actions.
        Args:
            initial_video: (T, 3, H, W) past observation clip
            future_robot_actions: (H_steps, D_action) candidate control sequence
        Returns:
            predicted_latents: (H_steps, N_patches, D) predicted latent tokens
        """
        H_steps = len(future_robot_actions)
        if not HAS_TORCH:
            return np.zeros((H_steps, 49, self.config.embed_dim), dtype=np.float32)

        with torch.no_grad():
            if initial_video.ndim == 4 and initial_video.shape[-1] == 3:
                initial_video = np.transpose(initial_video, (0, 3, 1, 2))
            v_t = torch.from_numpy(initial_video).unsqueeze(0).float()
            ctx = self.model.context_encoder(v_t)

            num_patches = (self.config.image_size[0] // self.config.patch_size) ** 2
            ctx_idx = torch.arange(ctx.size(1))
            tgt_idx = torch.arange(num_patches)
            act_t = torch.from_numpy(future_robot_actions).unsqueeze(0).float()

            pred_latent = self.model.predictor(ctx, ctx_idx, tgt_idx, act_t)
            return pred_latent.squeeze(0).cpu().numpy()
