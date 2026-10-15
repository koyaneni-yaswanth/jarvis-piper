"""
JARVIS-PiPER Perception subsystem.

Exports:
- JarvisPerceptionDetector  : YOLO + depth-deprojection object detector (existing)
- CameraSource              : Abstract camera source interface (new)
- RealsenseCamera           : Intel RealSense D405 adapter (new)
- UsbCamera                 : DECXIN / Sunplus USB camera adapter (new)
- RecordedCamera            : Replay from image files or directory (new)
- MockCamera                : Deterministic synthetic frames for tests (new)
- build_camera_source       : Factory function (new)
"""

from jarvis_piper.perception.detector import JarvisPerceptionDetector
from jarvis_piper.perception.camera import (
    CameraSource,
    CameraFrame,
    ColorFormat,
    CameraUnavailableError,
    CameraNotOpenError,
    RealsenseCamera,
    UsbCamera,
    RecordedCamera,
    MockCamera,
    build_camera_source,
)
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

__all__ = [
    "JarvisPerceptionDetector",
    "CameraSource",
    "CameraFrame",
    "ColorFormat",
    "CameraUnavailableError",
    "CameraNotOpenError",
    "RealsenseCamera",
    "UsbCamera",
    "RecordedCamera",
    "MockCamera",
    "build_camera_source",
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
]

