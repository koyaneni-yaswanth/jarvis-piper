"""
JARVIS-PiPER Episode-Level Dataset Splitter.
Splits episodes into train / val / test / OOD splits (never splitting intra-episode frames).
"""

import glob
import json
import os
import random
from typing import Dict, List


class DatasetSplitter:
    """Partitions episodes across splits."""

    def __init__(self, raw_dir: str, splits_dir: str = "dataset/splits"):
        self.raw_dir = raw_dir
        self.splits_dir = splits_dir
        os.makedirs(self.splits_dir, exist_ok=True)

    def create_splits(
        self,
        train_ratio: float = 0.8,
        val_ratio: float = 0.1,
        test_ratio: float = 0.1,
        seed: int = 42,
    ) -> Dict[str, List[str]]:
        ep_dirs = sorted(glob.glob(os.path.join(self.raw_dir, "ep_*")))
        ep_ids = [os.path.basename(d) for d in ep_dirs]

        rng = random.Random(seed)
        rng.shuffle(ep_ids)

        N = len(ep_ids)
        n_train = int(N * train_ratio)
        n_val = int(N * val_ratio)

        splits = {
            "train": ep_ids[:n_train],
            "val": ep_ids[n_train : n_train + n_val],
            "test": ep_ids[n_train + n_val :],
            "ood_test": [e for e in ep_ids if "ood" in e.lower()],
        }

        for split_name, ids in splits.items():
            path = os.path.join(self.splits_dir, f"{split_name}.json")
            with open(path, "w", encoding="utf-8") as f:
                json.dump({"split": split_name, "count": len(ids), "episodes": ids}, f, indent=2)

        return splits
