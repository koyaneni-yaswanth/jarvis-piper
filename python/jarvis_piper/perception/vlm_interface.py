"""
JARVIS-PiPER: Vision-Language Model (VLM) Interface.

Provides a model-independent abstraction over VLM capabilities:
- describe_image:             Pure image captioning
- answer_visual_question:     Image + question -> text answer
- match_image_to_candidates:  Text-image similarity ranking (NOT bounding boxes)
- detect_or_localize_objects: Object detection / localization request
                              (returns text descriptions, NOT robot coordinates)

Design principles:
1. Clear method boundaries: captioning ≠ question-answering ≠ similarity ≠ localization.
2. Similarity scores from CLIP are *cosine similarities*, not calibrated probabilities.
3. VLM output is untrusted perception text; it never reaches the arm directly.
4. All methods have explicit timeouts and return structured response objects.
5. Missing model weights raise ModelUnavailableError, never silently fall back.
6. Network access is explicitly opt-in (download_if_missing flag).
"""

import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Error types
# ---------------------------------------------------------------------------

class VLMError(RuntimeError):
    """Base class for VLM interface errors."""


class ModelUnavailableError(VLMError):
    """Raised when the model weights or backend cannot be loaded."""


class InferenceTimeoutError(VLMError):
    """Raised when inference exceeds the configured time budget."""


class InvalidImageError(VLMError):
    """Raised when the input image is malformed, empty, or None."""


# ---------------------------------------------------------------------------
# Request / response schemas
# ---------------------------------------------------------------------------

class VLMRole(str, Enum):
    CAPTIONING = "captioning"
    VQA = "vqa"
    MATCHING = "matching"
    LOCALIZATION = "localization"


@dataclass
class CaptionResponse:
    """Result from describe_image."""
    caption: str
    confidence: Optional[float] = None  # Model-reported confidence if available
    latency_s: float = 0.0
    model_id: str = "unknown"
    warning: Optional[str] = None      # e.g. "low-res input"

    def __str__(self) -> str:
        return self.caption


@dataclass
class VQAResponse:
    """Result from answer_visual_question."""
    question: str
    answer: str
    latency_s: float = 0.0
    model_id: str = "unknown"
    warning: Optional[str] = None


@dataclass
class MatchCandidate:
    """A single candidate in a text-image matching result."""
    text: str
    score: float          # Cosine similarity in [-1, 1]; NOT a calibrated probability
    rank: int             # 1 = best match


@dataclass
class MatchResponse:
    """Result from match_image_to_candidates.

    IMPORTANT: `scores` are cosine similarities, not probabilities.
    The highest-scoring candidate is the best text-image match,
    but this does NOT guarantee the object is present in the image.
    """
    candidates: List[MatchCandidate] = field(default_factory=list)
    latency_s: float = 0.0
    model_id: str = "unknown"
    note: str = (
        "Scores are cosine similarities in [-1, 1]. "
        "They are not calibrated probabilities. "
        "Do not treat top-ranked candidate as a confirmed object detection."
    )


@dataclass
class LocalizationResult:
    """Result from detect_or_localize_objects.

    NOTE: Bounding boxes from language-guided detection are coarse.
    They must be validated before any coordinate transform to robot frame.
    """
    request: str
    description: str                          # Free-text model output
    bboxes: List[Dict[str, Any]] = field(default_factory=list)
    # Each bbox: {"label": str, "bbox_xyxy": [x1,y1,x2,y2], "confidence": float}
    latency_s: float = 0.0
    model_id: str = "unknown"
    warning: Optional[str] = None
    validated: bool = False  # True only when bbox has been verified by a separate validator


# ---------------------------------------------------------------------------
# Abstract VLM interface
# ---------------------------------------------------------------------------

class VisionLanguageModel(ABC):
    """
    Abstract Vision-Language Model interface for JARVIS-PiPER.

    Implementations must be model-independent. The safety supervisor
    treats all VLM output as untrusted perception.
    """

    def __init__(
        self,
        model_id: str,
        timeout_s: float = 30.0,
        download_if_missing: bool = False,
    ) -> None:
        self.model_id = model_id
        self.timeout_s = timeout_s
        self.download_if_missing = download_if_missing
        self._loaded: bool = False

    @abstractmethod
    def load(self) -> None:
        """Load model weights and initialize inference backend.

        Raises ModelUnavailableError if weights are absent and
        download_if_missing is False.
        """

    @abstractmethod
    def is_loaded(self) -> bool:
        """Return True if the model is ready for inference."""

    @abstractmethod
    def describe_image(self, image: np.ndarray) -> CaptionResponse:
        """Generate a textual description of the image.

        Parameters
        ----------
        image : np.ndarray
            H x W x 3 uint8 BGR image.

        Returns
        -------
        CaptionResponse

        Raises
        ------
        InvalidImageError
            If the image is None, empty, or has an unexpected shape.
        InferenceTimeoutError
            If inference exceeds timeout_s.
        """

    @abstractmethod
    def answer_visual_question(
        self, image: np.ndarray, question: str
    ) -> VQAResponse:
        """Answer a natural-language question about an image.

        Parameters
        ----------
        image : np.ndarray
            H x W x 3 uint8 BGR image.
        question : str
            Natural language question about the image content.

        Returns
        -------
        VQAResponse
        """

    @abstractmethod
    def match_image_to_candidates(
        self, image: np.ndarray, candidates: List[str]
    ) -> MatchResponse:
        """Rank candidate text descriptions by image-text similarity.

        Parameters
        ----------
        image : np.ndarray
            H x W x 3 uint8 BGR image.
        candidates : list of str
            Textual candidate descriptions to rank.

        Returns
        -------
        MatchResponse
            Ranked candidates with cosine similarity scores.
            Scores are NOT probabilities.
        """

    @abstractmethod
    def detect_or_localize_objects(
        self, image: np.ndarray, request: str
    ) -> LocalizationResult:
        """Attempt to detect or localize objects described in a natural-language request.

        Parameters
        ----------
        image : np.ndarray
            H x W x 3 uint8 BGR image.
        request : str
            Natural language description of what to find
            (e.g. "find the red cube on the table").

        Returns
        -------
        LocalizationResult
            Text description and optional coarse bounding boxes.
            Bounding boxes from captioning models are unreliable.
            `validated` will be False unless an explicit validator confirms them.
        """

    # ------------------------------------------------------------------
    # Shared utilities
    # ------------------------------------------------------------------

    @staticmethod
    def _validate_image(image: Optional[np.ndarray]) -> np.ndarray:
        """Raise InvalidImageError if the image is unusable."""
        if image is None:
            raise InvalidImageError("Image is None.")
        if not isinstance(image, np.ndarray):
            raise InvalidImageError(
                f"Expected np.ndarray, got {type(image).__name__}."
            )
        if image.size == 0:
            raise InvalidImageError("Image array is empty (size=0).")
        if len(image.shape) not in (2, 3):
            raise InvalidImageError(
                f"Image must be 2-D (grayscale) or 3-D (color), "
                f"got shape {image.shape}."
            )
        return image

    @staticmethod
    def _bgr_to_rgb(image: np.ndarray) -> np.ndarray:
        """Convert BGR (OpenCV) to RGB (PIL / transformers convention)."""
        if len(image.shape) == 3 and image.shape[2] == 3:
            return image[:, :, ::-1].copy()
        return image

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"model_id={self.model_id!r}, "
            f"loaded={self.is_loaded()}, "
            f"timeout={self.timeout_s}s)"
        )
