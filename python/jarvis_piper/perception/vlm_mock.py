"""
JARVIS-PiPER: Mock VLM Adapter for Tests and MOCK Operating Mode.

Provides deterministic, hardware-free VLM responses suitable for:
- Unit tests (no model download required)
- CI pipelines (no GPU, no internet)
- MOCK operating mode
- Development iteration without waiting for model loads

All responses are configurable and reproducible. No weights are loaded.
"""

import time
from typing import List, Optional

import numpy as np

from jarvis_piper.perception.vlm_interface import (
    VisionLanguageModel,
    CaptionResponse,
    VQAResponse,
    MatchResponse,
    MatchCandidate,
    LocalizationResult,
    InvalidImageError,
    ModelUnavailableError,
)


class MockVLMAdapter(VisionLanguageModel):
    """
    Deterministic mock VLM adapter. No model weights required.

    Parameters
    ----------
    fixed_caption : str
        Caption returned by describe_image.
    fixed_answer : str
        Answer returned by answer_visual_question.
    fixed_top_candidate_index : int
        Index into candidates list returned as rank-1 by match_image_to_candidates.
    simulate_latency_s : float
        Simulated inference latency (default: 0.0 for fast tests).
    fail_on_empty_image : bool
        If True, raises InvalidImageError for a blank (all-zeros) image.
    """

    def __init__(
        self,
        model_id: str = "mock-vlm",
        fixed_caption: str = "a robotic tabletop with a red block and a bowl",
        fixed_answer: str = "yes",
        fixed_top_candidate_index: int = 0,
        simulate_latency_s: float = 0.0,
        fail_on_empty_image: bool = False,
    ) -> None:
        super().__init__(model_id=model_id, timeout_s=60.0, download_if_missing=False)
        self._fixed_caption = fixed_caption
        self._fixed_answer = fixed_answer
        self._fixed_top_idx = fixed_top_candidate_index
        self._simulate_latency_s = simulate_latency_s
        self._fail_on_empty = fail_on_empty_image

    def load(self) -> None:
        """No-op. Mock adapter is always ready."""
        self._loaded = True

    def is_loaded(self) -> bool:
        return True

    def describe_image(self, image: np.ndarray) -> CaptionResponse:
        self._validate_image(image)
        self._maybe_fail_empty(image)
        self._sleep()
        return CaptionResponse(
            caption=self._fixed_caption,
            confidence=0.95,
            latency_s=self._simulate_latency_s,
            model_id=self.model_id,
        )

    def answer_visual_question(
        self, image: np.ndarray, question: str
    ) -> VQAResponse:
        self._validate_image(image)
        self._maybe_fail_empty(image)
        self._sleep()
        return VQAResponse(
            question=question,
            answer=self._fixed_answer,
            latency_s=self._simulate_latency_s,
            model_id=self.model_id,
        )

    def match_image_to_candidates(
        self, image: np.ndarray, candidates: List[str]
    ) -> MatchResponse:
        self._validate_image(image)
        self._maybe_fail_empty(image)
        self._sleep()

        if not candidates:
            return MatchResponse(candidates=[], model_id=self.model_id)

        # Put the fixed top candidate at rank 1 with score 0.9, others at 0.5
        safe_idx = min(self._fixed_top_idx, len(candidates) - 1)
        result = []
        for i, cand in enumerate(candidates):
            score = 0.9 if i == safe_idx else 0.5 - (0.05 * i)
            result.append((score, cand))

        result.sort(key=lambda x: x[0], reverse=True)
        return MatchResponse(
            candidates=[
                MatchCandidate(text=cand, score=score, rank=rank + 1)
                for rank, (score, cand) in enumerate(result)
            ],
            latency_s=self._simulate_latency_s,
            model_id=self.model_id,
        )

    def detect_or_localize_objects(
        self, image: np.ndarray, request: str
    ) -> LocalizationResult:
        self._validate_image(image)
        self._maybe_fail_empty(image)
        self._sleep()
        return LocalizationResult(
            request=request,
            description=f"Mock: detected '{request}' in the scene (synthetic result).",
            bboxes=[
                {
                    "label": request,
                    "bbox_xyxy": [280, 220, 360, 300],
                    "confidence": 0.94,
                }
            ],
            latency_s=self._simulate_latency_s,
            model_id=self.model_id,
            warning="Mock detection. Do not use for robot coordinate transforms.",
            validated=False,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _sleep(self) -> None:
        if self._simulate_latency_s > 0.0:
            time.sleep(self._simulate_latency_s)

    def _maybe_fail_empty(self, image: np.ndarray) -> None:
        if self._fail_on_empty and image.sum() == 0:
            raise InvalidImageError(
                "MockVLMAdapter: received all-zeros image (fail_on_empty_image=True)."
            )
