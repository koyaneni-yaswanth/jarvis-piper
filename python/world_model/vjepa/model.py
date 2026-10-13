"""
V-JEPA (Video Joint-Embedding Predictive Architecture) Model.
Implements:
1. ViT Context Encoder (processes unmasked patches).
2. EMA Target Encoder (processes target video, provides latent ground truth).
3. Latent Predictor (predicts target patch representations from context + robot action).
"""

import copy
import math
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from .config import VJEPAConfig

try:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False
    class nn:  # type: ignore
        Module = object


if HAS_TORCH:
    class PatchEmbed3D(nn.Module):
        """
        Spatio-temporal patch embedding layer.
        Maps video tensor (B, C, T, H, W) to sequence of patch embeddings (B, N, D).
        """
        def __init__(self, img_size=(224, 224), patch_size=16, clip_length=16, in_chans=3, embed_dim=256):
            super().__init__()
            self.img_size = img_size
            self.patch_size = patch_size
            self.temporal_patch_size = 2
            self.grid_size = (
                clip_length // self.temporal_patch_size,
                img_size[0] // patch_size,
                img_size[1] // patch_size,
            )
            self.num_patches = self.grid_size[0] * self.grid_size[1] * self.grid_size[2]

            self.proj = nn.Conv3d(
                in_chans,
                embed_dim,
                kernel_size=(self.temporal_patch_size, patch_size, patch_size),
                stride=(self.temporal_patch_size, patch_size, patch_size),
            )

        def forward(self, x: torch.Tensor) -> torch.Tensor:
            # x: (B, T, C, H, W) -> permute to (B, C, T, H, W)
            x = x.permute(0, 2, 1, 3, 4)
            x = self.proj(x)  # (B, D, T', H', W')
            x = x.flatten(2).transpose(1, 2)  # (B, N, D)
            return x

    class TransformerBlock(nn.Module):
        def __init__(self, dim: int, num_heads: int, mlp_ratio: float = 4.0):
            super().__init__()
            self.norm1 = nn.LayerNorm(dim)
            self.attn = nn.MultiheadAttention(dim, num_heads, batch_first=True)
            self.norm2 = nn.LayerNorm(dim)
            mlp_dim = int(dim * mlp_ratio)
            self.mlp = nn.Sequential(
                nn.Linear(dim, mlp_dim),
                nn.GELU(),
                nn.Linear(mlp_dim, dim),
            )

        def forward(self, x: torch.Tensor) -> torch.Tensor:
            norm_x = self.norm1(x)
            attn_out, _ = self.attn(norm_x, norm_x, norm_x)
            x = x + attn_out
            x = x + self.mlp(self.norm2(x))
            return x

    class ViTEncoder(nn.Module):
        """Context & Target ViT Backbone."""
        def __init__(self, config: VJEPAConfig):
            super().__init__()
            self.config = config
            self.patch_embed = PatchEmbed3D(
                img_size=tuple(config.image_size),
                patch_size=config.patch_size,
                clip_length=config.clip_length,
                embed_dim=config.embed_dim,
            )
            num_patches = self.patch_embed.num_patches
            self.pos_embed = nn.Parameter(torch.zeros(1, num_patches, config.embed_dim))
            self.blocks = nn.ModuleList([
                TransformerBlock(config.embed_dim, config.num_heads)
                for _ in range(config.depth)
            ])
            self.norm = nn.LayerNorm(config.embed_dim)
            self._init_weights()

        def _init_weights(self):
            nn.init.trunc_normal_(self.pos_embed, std=0.02)

        def forward(self, x: torch.Tensor, indices: Optional[torch.Tensor] = None) -> torch.Tensor:
            """
            Args:
                x: (B, T, C, H, W)
                indices: Optional subset of patch indices to process (Context masking)
            """
            B = x.shape[0]
            tokens = self.patch_embed(x)  # (B, N, D)
            tokens = tokens + self.pos_embed

            if indices is not None:
                # Gather specific context patches
                # indices: (B, K) or (K,)
                if indices.dim() == 1:
                    indices = indices.unsqueeze(0).expand(B, -1)
                idx_expanded = indices.unsqueeze(-1).expand(-1, -1, tokens.size(-1))
                tokens = torch.gather(tokens, dim=1, index=idx_expanded)

            for blk in self.blocks:
                tokens = blk(tokens)
            tokens = self.norm(tokens)
            return tokens

    class LatentPredictor(nn.Module):
        """
        Lightweight Transformer Predictor that maps context tokens + mask queries
        + robot proprioceptive state to target latent representations.
        """
        def __init__(self, config: VJEPAConfig):
            super().__init__()
            self.config = config
            self.in_proj = nn.Linear(config.embed_dim, config.predictor_embed_dim)
            self.mask_token = nn.Parameter(torch.zeros(1, 1, config.predictor_embed_dim))
            self.pos_embed = nn.Parameter(
                torch.zeros(1, (config.clip_length // 2) * (config.image_size[0] // config.patch_size) * (config.image_size[1] // config.patch_size), config.predictor_embed_dim)
            )

            # Robot action / state conditioning projection
            if config.include_robot_state:
                self.robot_state_proj = nn.Linear(config.robot_state_dim, config.predictor_embed_dim)
            else:
                self.robot_state_proj = None

            self.blocks = nn.ModuleList([
                TransformerBlock(config.predictor_embed_dim, config.predictor_num_heads)
                for _ in range(config.predictor_depth)
            ])
            self.out_proj = nn.Linear(config.predictor_embed_dim, config.embed_dim)
            self.norm = nn.LayerNorm(config.predictor_embed_dim)
            self._init_weights()

        def _init_weights(self):
            nn.init.trunc_normal_(self.mask_token, std=0.02)
            nn.init.trunc_normal_(self.pos_embed, std=0.02)

        def forward(
            self,
            context_repr: torch.Tensor,
            context_indices: torch.Tensor,
            target_indices: Optional[torch.Tensor] = None,
            robot_state: Optional[torch.Tensor] = None,
        ) -> torch.Tensor:
            """
            Predicts representations of target tokens.
            """
            B = context_repr.size(0)
            ctx = self.in_proj(context_repr)

            # Add positional embeddings to context
            if context_indices.dim() == 1:
                context_indices = context_indices.unsqueeze(0).expand(B, -1)
            ctx_pos = torch.gather(
                self.pos_embed.expand(B, -1, -1),
                1,
                context_indices.unsqueeze(-1).expand(-1, -1, self.pos_embed.size(-1))
            )
            ctx = ctx + ctx_pos

            # Target queries: mask_token + target pos_embed
            if target_indices is None:
                target_indices = context_indices
            if target_indices.dim() == 1:
                target_indices = target_indices.unsqueeze(0).expand(B, -1)
            K_tgt = target_indices.size(1)
            tgt_pos = torch.gather(
                self.pos_embed.expand(B, -1, -1),
                1,
                target_indices.unsqueeze(-1).expand(-1, -1, self.pos_embed.size(-1))
            )
            tgt = self.mask_token.expand(B, K_tgt, -1) + tgt_pos

            # Robot state token if available
            tokens_list = [ctx, tgt]
            if self.robot_state_proj is not None and robot_state is not None:
                # Ensure 3D (B, seq, dim)
                if robot_state.dim() == 2:
                    robot_state = robot_state.unsqueeze(1)
                # Pad or slice to match robot_state_proj in_features
                in_f = self.robot_state_proj.in_features
                if robot_state.size(-1) < in_f:
                    pad = torch.zeros(*robot_state.shape[:-1], in_f - robot_state.size(-1), device=robot_state.device, dtype=robot_state.dtype)
                    robot_state = torch.cat([robot_state, pad], dim=-1)
                elif robot_state.size(-1) > in_f:
                    robot_state = robot_state[..., :in_f]
                # Pool across clip sequence
                r_token = self.robot_state_proj(robot_state).mean(dim=1, keepdim=True)
                tokens_list.insert(0, r_token)

            tokens = torch.cat(tokens_list, dim=1)

            for blk in self.blocks:
                tokens = blk(tokens)
            tokens = self.norm(tokens)

            # Extract target predictions
            offset = 1 if (self.robot_state_proj is not None and robot_state is not None) else 0
            tgt_preds = tokens[:, offset + ctx.size(1):]
            pred_reps = self.out_proj(tgt_preds)
            return pred_reps


class VJEPAModel:
    """
    Main V-JEPA Wrapper combining Context Encoder, Target Encoder, and Predictor.
    Provides PyTorch implementation or zero-dependency mock mode.
    """

    def __init__(self, config: VJEPAConfig):
        self.config = config
        self.has_torch = HAS_TORCH

        if HAS_TORCH:
            self.context_encoder = ViTEncoder(config)
            self.target_encoder = copy.deepcopy(self.context_encoder)
            # Freeze target encoder weights (updated strictly via EMA)
            for p in self.target_encoder.parameters():
                p.requires_grad = False
            self.predictor = LatentPredictor(config)
        else:
            self.context_encoder = None
            self.target_encoder = None
            self.predictor = None

    def update_target_encoder(self, momentum: Optional[float] = None):
        """Applies EMA update: target = momentum * target + (1 - momentum) * context"""
        if not HAS_TORCH:
            return
        m = momentum if momentum is not None else self.config.ema_decay
        with torch.no_grad():
            for p_ctx, p_tgt in zip(self.context_encoder.parameters(), self.target_encoder.parameters()):
                p_tgt.data.mul_(m).add_(p_ctx.data, alpha=1.0 - m)

    def forward(
        self,
        video: Any,
        context_indices: Any,
        target_indices: Any,
        robot_state: Optional[Any] = None,
    ) -> Tuple[Any, Any]:
        """
        Returns:
            predicted_targets: Tensor of predicted latent targets (B, K_tgt, D)
            ground_truth_targets: Tensor of target representations from EMA encoder (B, K_tgt, D)
        """
        if not HAS_TORCH:
            # Fallback zero-dependency simulated output
            B = 1 if isinstance(video, np.ndarray) and video.ndim == 4 else getattr(video, "shape", [1])[0]
            K_tgt = len(target_indices) if hasattr(target_indices, "__len__") else 10
            D = self.config.embed_dim
            pred = np.zeros((B, K_tgt, D), dtype=np.float32)
            target = np.zeros((B, K_tgt, D), dtype=np.float32)
            return pred, target

        # 1. Target representations from frozen Target Encoder
        with torch.no_grad():
            target_reps = self.target_encoder(video, target_indices)
            # Normalize target representations
            target_reps = F.layer_norm(target_reps, (target_reps.size(-1),))

        # 2. Context representations from Context Encoder
        context_reps = self.context_encoder(video, context_indices)

        # 3. Predictor rollout
        pred_reps = self.predictor(context_reps, context_indices, target_indices, robot_state)

        return pred_reps, target_reps

    def to(self, device: str):
        if HAS_TORCH:
            self.context_encoder.to(device)
            self.target_encoder.to(device)
            self.predictor.to(device)
        return self

    def train_mode(self):
        if HAS_TORCH:
            self.context_encoder.train()
            self.predictor.train()

    def eval_mode(self):
        if HAS_TORCH:
            self.context_encoder.eval()
            self.target_encoder.eval()
            self.predictor.eval()
