"""
Module A: V-JEPA Visual Representation Extraction.
Loads compatible pretrained V-JEPA / ViT spatio-temporal encoder.
Extracts representation tokens from video frames, saving structured embeddings.
"""

import os
import json
from typing import Dict, Any, Optional, List, Tuple
import numpy as np

try:
    import torch
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False

try:
    import cv2
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False

import sys
_py_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "python"))
if _py_dir not in sys.path:
    sys.path.insert(0, _py_dir)

from world_model.vjepa.config import VJEPAConfig
from world_model.vjepa.model import VJEPAModel


class VJEPAVisualEncoder:
    """
    Dedicated visual encoder for extracting latent representation tokens from video sequences.
    """

    def __init__(self, config: Optional[VJEPAConfig] = None, checkpoint_path: Optional[str] = None):
        self.config = config or VJEPAConfig()
        self.model = VJEPAModel(self.config)
        self.model.eval_mode()
        self.device = "cuda" if (HAS_TORCH and torch.cuda.is_available()) else "cpu"

        if HAS_TORCH:
            self.model.to(self.device)

        if HAS_TORCH and checkpoint_path and os.path.exists(checkpoint_path):
            try:
                ckpt = torch.load(checkpoint_path, map_location=self.device)
                if "context_encoder" in ckpt:
                    self.model.context_encoder.load_state_dict(ckpt["context_encoder"])
            except Exception:
                pass

    def extract_embedding(self, video_frames: np.ndarray) -> np.ndarray:
        """
        Encodes a video clip into a latent embedding vector.
        video_frames: (T, H, W, 3) or (T, 3, H, W)
        Returns:
            latent_vector: (D,) 1D pooled latent representation
        """
        if not HAS_TORCH:
            return np.zeros(self.config.embed_dim, dtype=np.float32)

        # Preprocess to (T=16, 3, 224, 224)
        if video_frames.ndim == 4 and video_frames.shape[-1] == 3:
            v_in = video_frames
        elif video_frames.ndim == 4 and video_frames.shape[1] == 3:
            v_in = np.transpose(video_frames, (0, 2, 3, 1))
        else:
            v_in = video_frames

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

        video_tensor = np.stack(processed[:self.config.clip_length], axis=0)  # (T, 3, H, W)

        with torch.no_grad():
            v_t = torch.from_numpy(video_tensor).unsqueeze(0).float().to(self.device)
            tokens = self.model.context_encoder(v_t)  # (1, N_tokens, D)
            pooled = tokens.mean(dim=1).squeeze(0).cpu().numpy()
            return pooled

    def save_episode_embeddings(
        self,
        episode_id: str,
        video_frames: np.ndarray,
        output_dir: str = "data/embeddings",
    ) -> str:
        """Saves extracted embeddings with episode metadata."""
        os.makedirs(output_dir, exist_ok=True)
        embedding = self.extract_embedding(video_frames)
        save_path = os.path.join(output_dir, f"{episode_id}_embedding.npz")
        np.savez_compressed(save_path, episode_id=episode_id, embedding=embedding)
        return save_path
