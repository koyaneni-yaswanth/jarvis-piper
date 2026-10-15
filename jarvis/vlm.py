"""
JARVIS-PiPER VLM Integration Layer for `jarvis` package.
"""

import sys
from pathlib import Path

_repo_python_dir = str(Path(__file__).resolve().parent.parent / "python")
if _repo_python_dir not in sys.path:
    sys.path.insert(0, _repo_python_dir)

from jarvis_piper.perception.vlm_interface import (

    VisionLanguageModel,
    CaptionResponse,
    VQAResponse,
    MatchResponse,
    MatchCandidate,
    LocalizationResult,
    VLMError,
    ModelUnavailableError,
    InferenceTimeoutError,
    InvalidImageError,
    VLMRole,
)
from jarvis_piper.perception.vlm_mock import MockVLMAdapter
from jarvis_piper.perception.vlm_blip import BLIPAdapter
from jarvis_piper.perception.vlm_clip import CLIPAdapter
from jarvis_piper.perception.vlm_factory import (
    build_vlm,
    detect_hardware,
    MODEL_REGISTRY,
    HardwareProfile,
    ModelSpec,
)
from jarvis_piper.perception.camera import (
    CameraSource,
    CameraFrame,
    ColorFormat,
    MockCamera,
    build_camera_source,
)
from jarvis_piper.tasks.vlm_planner import (
    VisionTaskPlanner,
    TaskPlan,
    PlanStep,
    StepStatus,
    TaskType,
    classify_task,
)

__all__ = [
    "VisionLanguageModel",
    "CaptionResponse",
    "VQAResponse",
    "MatchResponse",
    "MatchCandidate",
    "LocalizationResult",
    "VLMError",
    "ModelUnavailableError",
    "InferenceTimeoutError",
    "InvalidImageError",
    "VLMRole",
    "MockVLMAdapter",
    "BLIPAdapter",
    "CLIPAdapter",
    "build_vlm",
    "detect_hardware",
    "MODEL_REGISTRY",
    "HardwareProfile",
    "ModelSpec",
    "CameraSource",
    "CameraFrame",
    "ColorFormat",
    "MockCamera",
    "build_camera_source",
    "VisionTaskPlanner",
    "TaskPlan",
    "PlanStep",
    "StepStatus",
    "TaskType",
    "classify_task",
]
