"""
JARVIS-PiPER Versioned Dataset Schema & Provenance Tags.
Distinguishes between OBSERVED, DERIVED, INFERRED, and ANNOTATED fields.
Includes dataclasses and directory validators.
"""

from enum import Enum
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List, Optional
from pathlib import Path
import json


class FieldSource(Enum):
    OBSERVED = "OBSERVED"   # Direct hardware / sensor telemetry
    DERIVED = "DERIVED"     # Computed deterministically (e.g. forward kinematics)
    INFERRED = "INFERRED"   # Predicted by neural models (e.g. bounding boxes)
    ANNOTATED = "ANNOTATED" # Human labeled (e.g. task instruction, success)


@dataclass
class EpisodeMetadata:
    episode_id: str
    task_instruction: str
    task_category: str = "manipulation"
    operator_id: str = "operator"
    source_label: str = "OBSERVED"
    robot_platform: str = "PiPER_6DOF"
    success_label: bool = True
    duration_sec: float = 0.0
    total_steps: int = 0
    target_fps: float = 50.0
    schema_version: str = "2.0.0"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class TCPPose:
    position: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    orientation: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0, 1.0])

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Timestep:
    step_index: int
    timestamp: float
    joint_positions: List[float]
    joint_velocities: List[float] = field(default_factory=lambda: [0.0] * 6)
    joint_efforts: List[float] = field(default_factory=lambda: [0.0] * 6)
    gripper_stroke: float = 0.0
    tcp_pose: Optional[TCPPose] = None
    action: List[float] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        if self.tcp_pose:
            d["tcp_pose"] = self.tcp_pose.to_dict()
        return d


def validate_episode_directory(ep_dir: Path) -> bool:
    """Verifies that an episode folder contains metadata and trajectory/stream logs."""
    ep_dir = Path(ep_dir)
    if not ep_dir.is_dir():
        return False
    return (ep_dir / "metadata.json").exists() and (
        (ep_dir / "trajectory.json").exists() or (ep_dir / "stream_journal.jsonl").exists()
    )


SCHEMA_V2 = {
    "version": "2.0.0",
    "metadata": {
        "episode_id": FieldSource.OBSERVED.value,
        "task_instruction": FieldSource.ANNOTATED.value,
        "operator_id": FieldSource.ANNOTATED.value,
        "robot_platform": FieldSource.OBSERVED.value,
        "source_label": FieldSource.ANNOTATED.value,
        "success_label": FieldSource.ANNOTATED.value,
        "target_fps": FieldSource.OBSERVED.value,
    },
    "observations": {
        "timestamp": FieldSource.OBSERVED.value,
        "joint_positions": FieldSource.OBSERVED.value,
        "joint_velocities": FieldSource.OBSERVED.value,
        "joint_efforts": FieldSource.OBSERVED.value,
        "gripper_stroke": FieldSource.OBSERVED.value,
        "tcp_pose": FieldSource.DERIVED.value,
        "rgb_images": FieldSource.OBSERVED.value,
        "depth_images": FieldSource.OBSERVED.value,
        "semantic_phase": FieldSource.DERIVED.value,
    },
    "actions": {
        "commanded_joints": FieldSource.OBSERVED.value,
        "commanded_gripper": FieldSource.OBSERVED.value,
        "teleop_pose": FieldSource.OBSERVED.value,
    },
}
