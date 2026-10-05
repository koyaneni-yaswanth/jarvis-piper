"""
V-JEPA Model and Training Configuration.
"""

from dataclasses import dataclass, field
from typing import List, Optional
import yaml


@dataclass
class VJEPAConfig:
    # Architecture
    patch_size: int = 16
    embed_dim: int = 256
    num_heads: int = 4
    depth: int = 4
    predictor_embed_dim: int = 128
    predictor_depth: int = 3
    predictor_num_heads: int = 4
    ema_decay: float = 0.996

    # Masking
    mask_ratio_spatial: float = 0.60
    mask_ratio_temporal: float = 0.50

    # Data
    dataset_dir: str = "dataset/raw"
    clip_length: int = 16
    frame_stride: int = 2
    image_size: List[int] = field(default_factory=lambda: [224, 224])
    include_robot_state: bool = True
    robot_state_dim: int = 8

    # Training
    epochs: int = 5
    batch_size: int = 2
    learning_rate: float = 1e-4
    weight_decay: float = 0.05
    checkpoint_frequency: int = 5
    output_dir: str = "models/checkpoints/vjepa"
    device: str = "auto"

    @classmethod
    def from_yaml(cls, yaml_path: str) -> "VJEPAConfig":
        with open(yaml_path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f)

        m = raw.get("model", {})
        d = raw.get("data", {})
        t = raw.get("training", {})

        return cls(
            patch_size=m.get("patch_size", 16),
            embed_dim=m.get("embed_dim", 256),
            num_heads=m.get("num_heads", 4),
            depth=m.get("depth", 4),
            predictor_embed_dim=m.get("predictor_embed_dim", 128),
            predictor_depth=m.get("predictor_depth", 3),
            predictor_num_heads=m.get("predictor_num_heads", 4),
            ema_decay=m.get("ema_decay", 0.996),
            mask_ratio_spatial=m.get("mask_ratio_spatial", 0.6),
            mask_ratio_temporal=m.get("mask_ratio_temporal", 0.5),
            dataset_dir=d.get("dataset_dir", "dataset/raw"),
            clip_length=d.get("clip_length", 16),
            frame_stride=d.get("frame_stride", 2),
            image_size=d.get("image_size", [224, 224]),
            include_robot_state=d.get("include_robot_state", True),
            robot_state_dim=d.get("robot_state_dim", 8),
            epochs=t.get("epochs", 5),
            batch_size=t.get("batch_size", 2),
            learning_rate=float(t.get("learning_rate", 1e-4)),
            weight_decay=float(t.get("weight_decay", 0.05)),
            checkpoint_frequency=t.get("checkpoint_frequency", 5),
            output_dir=t.get("output_dir", "models/checkpoints/vjepa"),
            device=t.get("device", "auto"),
        )
