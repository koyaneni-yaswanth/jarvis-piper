"""
JARVIS-PiPER: CLIP Text-Image Matching Adapter.

Uses OpenAI CLIP (ViT-B/32 or configurable variant) for text-image similarity.

Model: openai/clip-vit-base-patch32 (~338 MB)
Task:  Text-image cosine similarity ranking
CPU inference supported: yes (~200-500 ms on Core i7)
GPU: CUDA if available, else CPU

Important:
- CLIP scores are cosine similarities in [-1, 1].
- They are NOT calibrated probabilities.
- The top-ranked candidate is the closest textual match, NOT a guaranteed detection.
- CLIP does not produce bounding boxes.
- Use for ranking hypotheses, not for robot-coordinate generation.
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

_CLIP_DEFAULT_MODEL_ID = "openai/clip-vit-base-patch32"


class CLIPAdapter(VisionLanguageModel):
    """
    CLIP text-image similarity adapter.

    Primary method: match_image_to_candidates — ranks candidate text strings
    by their cosine similarity to the image embedding.

    describe_image and answer_visual_question are not directly supported
    by CLIP; they are approximated using the highest-scoring candidate
    from a set of generic scene descriptions.

    Parameters
    ----------
    model_id : str
        HuggingFace model ID for CLIP. Default: openai/clip-vit-base-patch32.
    cache_dir : str | None
        Local directory for cached weights.
    download_if_missing : bool
        If False, raises ModelUnavailableError when not cached locally.
    timeout_s : float
        Per-inference time limit.
    force_cpu : bool
        Force CPU even when CUDA is available.
    """

    def __init__(
        self,
        model_id: str = _CLIP_DEFAULT_MODEL_ID,
        cache_dir: Optional[str] = None,
        download_if_missing: bool = False,
        timeout_s: float = 30.0,
        force_cpu: bool = False,
    ) -> None:
        super().__init__(
            model_id=model_id,
            timeout_s=timeout_s,
            download_if_missing=download_if_missing,
        )
        self._cache_dir = cache_dir
        self._force_cpu = force_cpu
        self._model = None
        self._processor = None
        self._device: Optional[str] = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load(self) -> None:
        """Load CLIP weights from cache or HuggingFace Hub."""
        try:
            import torch  # type: ignore[import]
            from transformers import CLIPModel, CLIPProcessor  # type: ignore[import]
        except ImportError as exc:
            raise ModelUnavailableError(
                "CLIP requires 'torch' and 'transformers'. "
                "Install with: pip install torch transformers"
            ) from exc

        self._device = (
            "cpu"
            if (self._force_cpu or not torch.cuda.is_available())
            else "cuda"
        )
        logger.info("CLIP: using device=%s", self._device)

        if not self.download_if_missing:
            self._assert_weights_cached(self.model_id)

        logger.info("Loading CLIP model: %s", self.model_id)
        t0 = time.monotonic()
        try:
            self._processor = CLIPProcessor.from_pretrained(
                self.model_id,
                cache_dir=self._cache_dir,
                local_files_only=(not self.download_if_missing),
            )
            self._model = CLIPModel.from_pretrained(
                self.model_id,
                cache_dir=self._cache_dir,
                local_files_only=(not self.download_if_missing),
            ).to(self._device)
            self._model.eval()
        except Exception as exc:
            raise ModelUnavailableError(
                f"Failed to load CLIP model '{self.model_id}': {exc}. "
                f"Run with download_if_missing=True to fetch weights."
            ) from exc

        self._loaded = True
        logger.info("CLIP loaded in %.2f s.", time.monotonic() - t0)

    def is_loaded(self) -> bool:
        return self._model is not None and self._loaded

    def match_image_to_candidates(
        self, image: np.ndarray, candidates: List[str]
    ) -> MatchResponse:
        """
        Rank candidate text strings by cosine similarity to the image.

        Parameters
        ----------
        image : np.ndarray
            H x W x 3 uint8 BGR image.
        candidates : list of str
            Textual descriptions to rank against the image.

        Returns
        -------
        MatchResponse
            Ranked candidates with cosine similarity scores.

        Notes
        -----
        Scores are cosine similarities in [-1, 1] after L2 normalisation.
        They are NOT softmax probabilities.
        The top-ranked candidate is the closest textual match, but this
        does NOT confirm the object is present or localized in the scene.
        """
        self._validate_image(image)
        self._require_loaded()
        import torch  # type: ignore[import]
        from PIL import Image as PILImage  # type: ignore[import]

        if not candidates:
            return MatchResponse(candidates=[], model_id=self.model_id)

        rgb = self._bgr_to_rgb(image)
        pil_img = PILImage.fromarray(rgb)

        t0 = time.monotonic()
        try:
            with torch.no_grad():
                inputs = self._processor(
                    text=candidates,
                    images=pil_img,
                    return_tensors="pt",
                    padding=True,
                ).to(self._device)

                outputs = self._model(**inputs)
                # logits_per_image: [1, num_candidates]
                logits = outputs.logits_per_image[0]
                # Convert to cosine similarity by undoing the temperature scale
                image_feat = outputs.image_embeds  # [1, D]
                text_feat = outputs.text_embeds    # [N, D]
                image_feat = image_feat / image_feat.norm(dim=-1, keepdim=True)
                text_feat = text_feat / text_feat.norm(dim=-1, keepdim=True)
                scores = (image_feat @ text_feat.T).squeeze(0)  # [N]
                scores_cpu = scores.cpu().numpy().tolist()
        except Exception as exc:
            raise InferenceTimeoutError(f"CLIP inference failed: {exc}") from exc

        latency = time.monotonic() - t0
        if latency > self.timeout_s:
            raise InferenceTimeoutError(
                f"CLIP inference took {latency:.1f}s, exceeding {self.timeout_s}s."
            )

        # Sort descending
        paired = sorted(
            zip(candidates, scores_cpu), key=lambda x: x[1], reverse=True
        )
        result_candidates = [
            MatchCandidate(text=text, score=float(score), rank=i + 1)
            for i, (text, score) in enumerate(paired)
        ]

        logger.debug(
            "CLIP match (%.2fs): top=%r (%.3f)",
            latency,
            result_candidates[0].text if result_candidates else "",
            result_candidates[0].score if result_candidates else 0.0,
        )
        return MatchResponse(
            candidates=result_candidates,
            latency_s=latency,
            model_id=self.model_id,
        )

    def describe_image(self, image: np.ndarray) -> CaptionResponse:
        """
        CLIP does not generate captions natively.

        Approximated by selecting the best match from a generic scene
        vocabulary. For proper captioning, use BLIPAdapter.
        """
        self._validate_image(image)
        generic_candidates = [
            "a robotic tabletop manipulation scene",
            "a table with objects on it",
            "a close-up of a robotic arm workspace",
            "an outdoor scene",
            "an indoor room",
            "electronic equipment",
            "food or kitchen items",
        ]
        match = self.match_image_to_candidates(image, generic_candidates)
        best = match.candidates[0] if match.candidates else MatchCandidate("unknown", 0.0, 1)
        return CaptionResponse(
            caption=best.text,
            confidence=best.score,
            latency_s=match.latency_s,
            model_id=self.model_id,
            warning=(
                "CLIP does not generate captions. "
                "This is the highest-scoring generic label, not a real caption. "
                "Use BLIPAdapter for captioning."
            ),
        )

    def answer_visual_question(
        self, image: np.ndarray, question: str
    ) -> VQAResponse:
        """
        CLIP does not support open-ended VQA.

        Falls back to ranking yes/no candidates, which is useful for binary
        questions only. For open-ended VQA use BLIPAdapter.
        """
        self._validate_image(image)
        candidates = [
            f"yes, {question}",
            f"no, not {question}",
        ]
        match = self.match_image_to_candidates(image, candidates)
        best = match.candidates[0] if match.candidates else MatchCandidate("unknown", 0.0, 1)
        answer = "yes" if "yes" in best.text.lower() else "no"
        return VQAResponse(
            question=question,
            answer=answer,
            latency_s=match.latency_s,
            model_id=self.model_id,
            warning=(
                "CLIP VQA is limited to binary yes/no approximations. "
                "Use BLIPAdapter for open-ended visual question answering."
            ),
        )

    def detect_or_localize_objects(
        self, image: np.ndarray, request: str
    ) -> LocalizationResult:
        """
        Use CLIP similarity to determine whether the requested object may be present.

        Returns a text description of the top-matching label. No bounding boxes.
        `validated` is always False.
        """
        self._validate_image(image)
        presence_candidates = [
            f"a photo containing {request}",
            f"a photo without {request}",
            f"an image with {request} visible",
        ]
        match = self.match_image_to_candidates(image, presence_candidates)
        top = match.candidates[0] if match.candidates else MatchCandidate("unknown", 0.0, 1)

        return LocalizationResult(
            request=request,
            description=top.text,
            bboxes=[],
            latency_s=match.latency_s,
            model_id=self.model_id,
            warning=(
                "CLIP does not localize objects. "
                "This result is a text-image similarity judgment only. "
                "Do not use for robot coordinate transforms."
            ),
            validated=False,
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _require_loaded(self) -> None:
        if not self.is_loaded():
            raise ModelUnavailableError(
                "CLIPAdapter is not loaded. Call load() first."
            )

    def _assert_weights_cached(self, model_id: str) -> None:
        """Check HuggingFace cache before attempting network download."""
        from pathlib import Path

        cache_root = (
            Path(self._cache_dir)
            if self._cache_dir
            else Path.home() / ".cache" / "huggingface" / "hub"
        )
        model_folder = "models--" + model_id.replace("/", "--")
        candidate = cache_root / model_folder

        if not candidate.exists():
            raise ModelUnavailableError(
                f"CLIP weights for '{model_id}' not found in cache at {candidate}. "
                f"To download: create CLIPAdapter(download_if_missing=True) "
                f"or run: python -c \"from transformers import CLIPModel; "
                f"CLIPModel.from_pretrained('{model_id}')\""
            )
        logger.info("CLIP weights found in cache: %s", candidate)
