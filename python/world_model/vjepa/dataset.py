"""
V-JEPA Video Dataset and Spatio-Temporal Masking Generator.
Loads video clips and robot state trajectories from recorded episodes.
Supports PyTorch Dataset if torch is available, plus standalone NumPy generator.
"""

import os
import json
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
from .config import VJEPAConfig

try:
    import cv2
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False

try:
    import torch
    from torch.utils.data import Dataset
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False
    class Dataset:  # type: ignore
        pass


class SpatioTemporalMaskGenerator:
    """
    Generates spatio-temporal tube or block masks for V-JEPA training.
    Separates video patches into visible Context and masked Target regions.
    """

    def __init__(
        self,
        grid_size: Tuple[int, int, int] = (8, 14, 14),  # (T, H, W) patches
        spatial_mask_ratio: float = 0.60,
        temporal_mask_ratio: float = 0.50,
    ):
        self.T, self.H, self.W = grid_size
        self.num_patches = self.T * self.H * self.W
        self.spatial_mask_ratio = spatial_mask_ratio
        self.temporal_mask_ratio = temporal_mask_ratio

    def generate_mask(self) -> Tuple[np.ndarray, np.ndarray]:
        """
        Returns:
            context_indices: 1D array of indices kept for context encoder.
            target_indices: 1D array of indices predicted by latent predictor.
        """
        all_indices = np.arange(self.num_patches)
        num_target = int(self.num_patches * self.spatial_mask_ratio)
        
        # Block-wise or uniform sampling for target
        target_indices = np.random.choice(all_indices, size=num_target, replace=False)
        context_mask = np.ones(self.num_patches, dtype=bool)
        context_mask[target_indices] = False
        context_indices = all_indices[context_mask]

        return np.sort(context_indices), np.sort(target_indices)


class VJEPADataset(Dataset):
    """
    Multimodal video + robot state dataset loader for V-JEPA training.
    """

    def __init__(self, config: VJEPAConfig, root_dir: Optional[str] = None):
        self.config = config
        self.root_dir = Path(root_dir or config.dataset_dir)
        self.episodes: List[Path] = []
        self._discover_episodes()

        patch_h = config.image_size[0] // config.patch_size
        patch_w = config.image_size[1] // config.patch_size
        clip_patches_t = config.clip_length // 2  # Temporal patch stride
        self.mask_generator = SpatioTemporalMaskGenerator(
            grid_size=(max(1, clip_patches_t), patch_h, patch_w),
            spatial_mask_ratio=config.mask_ratio_spatial,
            temporal_mask_ratio=config.mask_ratio_temporal,
        )

    def _discover_episodes(self):
        if not self.root_dir.exists():
            return
        for ep_dir in sorted(self.root_dir.iterdir()):
            if ep_dir.is_dir() and (ep_dir / "metadata.json").exists():
                self.episodes.append(ep_dir)

    def __len__(self) -> int:
        return max(1, len(self.episodes))

    def _load_mock_clip(self) -> Dict[str, Any]:
        T = self.config.clip_length
        H, W = self.config.image_size
        D_state = self.config.robot_state_dim

        # Simulated synthetic frames (T, C, H, W) normalized to [-1, 1]
        video = np.random.uniform(-1.0, 1.0, size=(T, 3, H, W)).astype(np.float32)
        robot_state = np.random.uniform(-1.0, 1.0, size=(T, D_state)).astype(np.float32)
        ctx_idx, tgt_idx = self.mask_generator.generate_mask()

        sample = {
            "video": video,
            "robot_state": robot_state,
            "context_indices": ctx_idx,
            "target_indices": tgt_idx,
            "episode_id": "mock_episode_0000",
        }

        if HAS_TORCH:
            sample["video"] = torch.from_numpy(sample["video"])
            sample["robot_state"] = torch.from_numpy(sample["robot_state"])
            sample["context_indices"] = torch.from_numpy(sample["context_indices"]).long()
            sample["target_indices"] = torch.from_numpy(sample["target_indices"]).long()

        return sample

    def __getitem__(self, idx: int) -> Dict[str, Any]:
        if not self.episodes:
            return self._load_mock_clip()

        ep_dir = self.episodes[idx % len(self.episodes)]
        traj_file = ep_dir / "trajectory.json"
        video_file = ep_dir / "camera_wrist.mp4"

        frames: List[np.ndarray] = []
        if HAS_CV2 and video_file.exists():
            cap = cv2.VideoCapture(str(video_file))
            while cap.isOpened() and len(frames) < self.config.clip_length:
                ret, frame = cap.read()
                if not ret:
                    break
                frame = cv2.resize(frame, tuple(self.config.image_size[::-1]))
                frame = (frame.astype(np.float32) / 127.5) - 1.0
                frame = np.transpose(frame, (2, 0, 1))  # (3, H, W)
                frames.append(frame)
            cap.release()

        # Fallback if video is missing or too short
        while len(frames) < self.config.clip_length:
            H, W = self.config.image_size
            frames.append(np.zeros((3, H, W), dtype=np.float32))

        video = np.stack(frames[:self.config.clip_length], axis=0)  # (T, 3, H, W)

        robot_state = np.zeros((self.config.clip_length, self.config.robot_state_dim), dtype=np.float32)
        if traj_file.exists():
            try:
                with open(traj_file, "r") as f:
                    traj_data = json.load(f)
                states = traj_data.get("joint_positions", [])
                for i in range(min(len(states), self.config.clip_length)):
                    val = states[i]
                    robot_state[i, :len(val)] = val[:self.config.robot_state_dim]
            except Exception:
                pass

        ctx_idx, tgt_idx = self.mask_generator.generate_mask()
        sample = {
            "video": video,
            "robot_state": robot_state,
            "context_indices": ctx_idx,
            "target_indices": tgt_idx,
            "episode_id": ep_dir.name,
        }

        if HAS_TORCH:
            sample["video"] = torch.from_numpy(sample["video"])
            sample["robot_state"] = torch.from_numpy(sample["robot_state"])
            sample["context_indices"] = torch.from_numpy(sample["context_indices"]).long()
            sample["target_indices"] = torch.from_numpy(sample["target_indices"]).long()

        return sample
