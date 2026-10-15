"""
JARVIS-PiPER: BLIP Image Captioning Adapter.

Uses Salesforce BLIP-base for image captioning (describe_image) and
BLIP-VQA for visual question answering (answer_visual_question).

Model: Salesforce/blip-image-captioning-base (~990 MB)
Task:  Image captioning (NOT object detection, NOT bounding boxes)
CPU inference supported: yes (slow, ~2-8 s on Core i7/i5)
GPU: CUDA if available, else CPU

Important limitations:
- BLIP does NOT produce bounding boxes or spatial coordinates.
- BLIP VQA answers may be inaccurate for spatial reasoning.
- Captions describe the general scene, not fine-grained object positions.
- match_image_to_candidates is not supported by BLIP; use CLIPAdapter instead.
- detect_or_localize_objects returns a caption-based approximation, NOT real detection.
"""

import logging
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
    ModelUnavailableError,
    InferenceTimeoutError,
    InvalidImageError,
)

logger = logging.getLogger(__name__)

# Default model IDs from Hugging Face Hub
_BLIP_CAPTION_MODEL_ID = "Salesforce/blip-image-captioning-base"
_BLIP_VQA_MODEL_ID = "Salesforce/blip-vqa-base"


class BLIPAdapter(VisionLanguageModel):
    """
    BLIP image captioning and visual question-answering adapter.

    Parameters
    ----------
    caption_model_id : str
        HuggingFace model ID for captioning. Must be a BLIP captioning checkpoint.
    vqa_model_id : str
        HuggingFace model ID for VQA. Must be a BLIP VQA checkpoint.
    cache_dir : str | None
        Local directory to store / load cached weights.
        If None, uses HuggingFace default (~/.cache/huggingface/).
    download_if_missing : bool
        If False (default), raises ModelUnavailableError when weights are not
        found in cache_dir. If True, downloads from HuggingFace Hub.
    timeout_s : float
        Per-inference time limit in seconds.
    force_cpu : bool
        Force CPU execution even when CUDA is available.
    """

    def __init__(
        self,
        caption_model_id: str = _BLIP_CAPTION_MODEL_ID,
        vqa_model_id: str = _BLIP_VQA_MODEL_ID,
        cache_dir: Optional[str] = None,
        download_if_missing: bool = False,
        timeout_s: float = 30.0,
        force_cpu: bool = False,
    ) -> None:
        super().__init__(
            model_id=caption_model_id,
            timeout_s=timeout_s,
            download_if_missing=download_if_missing,
        )
        self._caption_model_id = caption_model_id
        self._vqa_model_id = vqa_model_id
        self._cache_dir = cache_dir
        self._force_cpu = force_cpu

        self._caption_model = None
        self._caption_processor = None
        self._vqa_model = None
        self._vqa_processor = None
        self._device: Optional[str] = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load(self) -> None:
        """Load BLIP weights. Raises ModelUnavailableError if not cached and
        download_if_missing is False."""
        try:
            import torch  # type: ignore[import]
            from transformers import (  # type: ignore[import]
                BlipForConditionalGeneration,
                BlipForQuestionAnswering,
                BlipProcessor,
            )
        except ImportError as exc:
            raise ModelUnavailableError(
                "BLIP requires 'torch' and 'transformers'. "
                "Install with: pip install torch transformers"
            ) from exc

        # Device selection
        if self._force_cpu or not torch.cuda.is_available():
            self._device = "cpu"
        else:
            self._device = "cuda"
        logger.info("BLIP: using device=%s", self._device)

        # Check cache before downloading
        if not self.download_if_missing:
            self._assert_weights_cached(self._caption_model_id)

        logger.info("Loading BLIP captioning model: %s", self._caption_model_id)
        t0 = time.monotonic()

        try:
            self._caption_processor = BlipProcessor.from_pretrained(
                self._caption_model_id,
                cache_dir=self._cache_dir,
                local_files_only=(not self.download_if_missing),
            )
            self._caption_model = BlipForConditionalGeneration.from_pretrained(
                self._caption_model_id,
                cache_dir=self._cache_dir,
                local_files_only=(not self.download_if_missing),
            ).to(self._device)
            self._caption_model.eval()
        except Exception as exc:
            raise ModelUnavailableError(
                f"Failed to load BLIP captioning model '{self._caption_model_id}': {exc}. "
                f"Run with download_if_missing=True to download, or verify cache_dir."
            ) from exc

        # VQA model (separate checkpoint)
        if not self.download_if_missing:
            self._assert_weights_cached(self._vqa_model_id)

        logger.info("Loading BLIP VQA model: %s", self._vqa_model_id)
        try:
            self._vqa_processor = BlipProcessor.from_pretrained(
                self._vqa_model_id,
                cache_dir=self._cache_dir,
                local_files_only=(not self.download_if_missing),
            )
            self._vqa_model = BlipForQuestionAnswering.from_pretrained(
                self._vqa_model_id,
                cache_dir=self._cache_dir,
                local_files_only=(not self.download_if_missing),
            ).to(self._device)
            self._vqa_model.eval()
        except Exception as exc:
            raise ModelUnavailableError(
                f"Failed to load BLIP VQA model '{self._vqa_model_id}': {exc}."
            ) from exc

        self._loaded = True
        logger.info(
            "BLIP models loaded in %.2f s (device=%s).",
            time.monotonic() - t0,
            self._device,
        )

    def is_loaded(self) -> bool:
        return (
            self._caption_model is not None
            and self._vqa_model is not None
            and self._loaded
        )

    def describe_image(self, image: np.ndarray) -> CaptionResponse:
        """Generate a caption for the image.

        Returns a free-text scene description. Does NOT produce
        bounding boxes or spatial coordinates.
        """
        self._validate_image(image)
        self._require_loaded()
        import torch  # type: ignore[import]
        from PIL import Image as PILImage  # type: ignore[import]

        rgb = self._bgr_to_rgb(image)
        pil_img = PILImage.fromarray(rgb)

        t0 = time.monotonic()
        try:
            with torch.no_grad():
                inputs = self._caption_processor(
                    images=pil_img, return_tensors="pt"
                ).to(self._device)
                ids = self._caption_model.generate(
                    **inputs,
                    max_new_tokens=64,
                )
                caption = self._caption_processor.decode(
                    ids[0], skip_special_tokens=True
                )
        except Exception as exc:
            raise InferenceTimeoutError(f"BLIP captioning failed: {exc}") from exc

        latency = time.monotonic() - t0
        if latency > self.timeout_s:
            raise InferenceTimeoutError(
                f"BLIP inference took {latency:.1f}s, exceeding timeout {self.timeout_s}s."
            )

        logger.debug("BLIP caption (%.2fs): %s", latency, caption)
        return CaptionResponse(
            caption=caption,
            latency_s=latency,
            model_id=self._caption_model_id,
        )

    def answer_visual_question(
        self, image: np.ndarray, question: str
    ) -> VQAResponse:
        """Answer a natural-language question about the image using BLIP-VQA."""
        self._validate_image(image)
        self._require_loaded()
        import torch  # type: ignore[import]
        from PIL import Image as PILImage  # type: ignore[import]

        rgb = self._bgr_to_rgb(image)
        pil_img = PILImage.fromarray(rgb)

        t0 = time.monotonic()
        try:
            with torch.no_grad():
                inputs = self._vqa_processor(
                    images=pil_img, text=question, return_tensors="pt"
                ).to(self._device)
                ids = self._vqa_model.generate(**inputs, max_new_tokens=32)
                answer = self._vqa_processor.decode(
                    ids[0], skip_special_tokens=True
                )
        except Exception as exc:
            raise InferenceTimeoutError(f"BLIP VQA failed: {exc}") from exc

        latency = time.monotonic() - t0
        logger.debug("BLIP VQA (%.2fs): Q=%r A=%r", latency, question, answer)
        return VQAResponse(
            question=question,
            answer=answer,
            latency_s=latency,
            model_id=self._vqa_model_id,
        )

    def match_image_to_candidates(
        self, image: np.ndarray, candidates: List[str]
    ) -> MatchResponse:
        """Not natively supported by BLIP.

        Falls back to answering 'what is in the image?' and returning
        the candidate closest to the caption using simple string matching.
        Use CLIPAdapter for proper text-image similarity.
        """
        self._validate_image(image)
        caption_resp = self.describe_image(image)
        caption_lower = caption_resp.caption.lower()

        scored = []
        for cand in candidates:
            # Simple word-overlap proxy (NOT cosine similarity)
            words = set(cand.lower().split())
            cap_words = set(caption_lower.split())
            overlap = len(words & cap_words) / max(len(words), 1)
            scored.append((cand, overlap))

        scored.sort(key=lambda x: x[1], reverse=True)
        candidates_out = [
            MatchCandidate(text=text, score=score, rank=i + 1)
            for i, (text, score) in enumerate(scored)
        ]

        return MatchResponse(
            candidates=candidates_out,
            latency_s=caption_resp.latency_s,
            model_id=self._caption_model_id,
            note=(
                "BLIP does not support text-image similarity. "
                "Scores are word-overlap proxies, not cosine similarities. "
                "Use CLIPAdapter for proper matching."
            ),
        )

    def detect_or_localize_objects(
        self, image: np.ndarray, request: str
    ) -> LocalizationResult:
        """
        Ask BLIP to describe the image with emphasis on the requested object.

        IMPORTANT: BLIP cannot produce reliable bounding boxes.
        This method returns a VQA-based text description only.
        `bboxes` will always be empty. `validated` will always be False.
        For actual detection use a YOLO or GroundingDINO adapter.
        """
        question = f"Is there a {request} in the image? Describe its location."
        vqa_resp = self.answer_visual_question(image, question)

        return LocalizationResult(
            request=request,
            description=vqa_resp.answer,
            bboxes=[],
            latency_s=vqa_resp.latency_s,
            model_id=self._vqa_model_id,
            warning=(
                "BLIP does not produce bounding boxes. "
                "Spatial description is text-only. "
                "Do not use this output for robot coordinate transforms."
            ),
            validated=False,
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _require_loaded(self) -> None:
        if not self.is_loaded():
            raise ModelUnavailableError(
                "BLIPAdapter is not loaded. Call load() first."
            )

    def _assert_weights_cached(self, model_id: str) -> None:
        """Check that the model is available locally before attempting to load."""
        import os
        from pathlib import Path

        # HuggingFace cache convention
        cache_root = (
            Path(self._cache_dir)
            if self._cache_dir
            else Path.home() / ".cache" / "huggingface" / "hub"
        )
        # Model folders are stored as models--org--name
        model_folder = "models--" + model_id.replace("/", "--")
        candidate = cache_root / model_folder

        if not candidate.exists():
            raise ModelUnavailableError(
                f"Model weights for '{model_id}' not found in cache at {candidate}. "
                f"To download: create BLIPAdapter(download_if_missing=True) "
                f"or run: python -c \"from transformers import BlipProcessor; "
                f"BlipProcessor.from_pretrained('{model_id}')\""
            )
        logger.info("BLIP weights found in cache: %s", candidate)
