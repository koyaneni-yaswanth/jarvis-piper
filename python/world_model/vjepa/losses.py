"""
V-JEPA Latent Loss Functions.
Implements L1 / Smooth-L1 latent space prediction loss and feature collapse regularization.
"""

import numpy as np
from typing import Tuple, Optional, Any

try:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False


class VJEPALoss:
    """
    Computes latent prediction error and optional representation variance regularization.
    """

    def __init__(self, loss_type: str = "l1", var_reg_weight: float = 0.01):
        self.loss_type = loss_type
        self.var_reg_weight = var_reg_weight

    def __call__(
        self,
        predicted: Any,
        target: Any,
    ) -> Any:
        """
        Args:
            predicted: (B, N_target, D) predicted latent tokens
            target: (B, N_target, D) target tokens from EMA encoder
        Returns:
            loss: scalar loss value (torch.Tensor or float)
        """
        if not HAS_TORCH:
            pred_arr = np.asarray(predicted)
            tgt_arr = np.asarray(target)
            return float(np.mean(np.abs(pred_arr - tgt_arr)))

        if not isinstance(predicted, torch.Tensor):
            predicted = torch.as_tensor(predicted, dtype=torch.float32)
        if not isinstance(target, torch.Tensor):
            target = torch.as_tensor(target, dtype=torch.float32)

        if self.loss_type == "l1":
            pred_loss = F.l1_loss(predicted, target)
        elif self.loss_type == "smooth_l1":
            pred_loss = F.smooth_l1_loss(predicted, target)
        else:
            pred_loss = F.mse_loss(predicted, target)

        # Variance regularization across tokens to prevent representation collapse
        if self.var_reg_weight > 0.0:
            # target std across batch and tokens
            std_pred = torch.sqrt(predicted.var(dim=[0, 1]) + 1e-4)
            std_loss = torch.mean(F.relu(1.0 - std_pred))
            total_loss = pred_loss + (self.var_reg_weight * std_loss)
            return total_loss

        return pred_loss
