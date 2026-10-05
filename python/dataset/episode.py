"""
JARVIS-PiPER Episode Representation.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class Episode:
    """In-memory representation of a single demonstration episode."""
    episode_id: str
    task_instruction: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    timesteps: List[Dict[str, Any]] = field(default_factory=list)
    wrist_video_path: Optional[str] = None
    overhead_video_path: Optional[str] = None

    def __len__(self) -> int:
        return len(self.timesteps)

    def __getitem__(self, idx: int) -> Dict[str, Any]:
        return self.timesteps[idx]

    @property
    def duration_sec(self) -> float:
        return float(self.metadata.get("duration_sec", len(self.timesteps) * 0.033))

    @property
    def is_successful(self) -> bool:
        return bool(self.metadata.get("success_label", True))
