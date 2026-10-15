"""
Tests for Vision-Language Model (VLM) Interface and Mock Adapter.
"""

import pytest
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
from jarvis_piper.perception.vlm_mock import MockVLMAdapter


def test_vlm_schemas():
    cap = CaptionResponse(caption="a robotic workspace", latency_s=0.1)
    assert str(cap) == "a robotic workspace"

    vqa = VQAResponse(question="Is there an apple?", answer="no", latency_s=0.05)
    assert vqa.answer == "no"

    cand = MatchCandidate(text="red cube", score=0.88, rank=1)
    match = MatchResponse(candidates=[cand], latency_s=0.02)
    assert len(match.candidates) == 1
    assert "cosine similarities" in match.note

    loc = LocalizationResult(
        request="find red cube",
        description="found red cube",
        bboxes=[{"label": "red cube", "bbox_xyxy": [10, 10, 50, 50], "confidence": 0.9}],
    )
    assert not loc.validated


def test_mock_vlm_adapter_operations():
    vlm = MockVLMAdapter(
        fixed_caption="test table with robot arm",
        fixed_answer="green",
        fixed_top_candidate_index=1,
    )
    vlm.load()
    assert vlm.is_loaded()

    img = np.ones((100, 100, 3), dtype=np.uint8) * 128

    # 1. describe_image
    cap = vlm.describe_image(img)
    assert cap.caption == "test table with robot arm"
    assert cap.confidence == 0.95

    # 2. answer_visual_question
    vqa = vlm.answer_visual_question(img, "What color is the block?")
    assert vqa.answer == "green"
    assert vqa.question == "What color is the block?"

    # 3. match_image_to_candidates
    candidates = ["blue mug", "red cube", "yellow bowl"]
    matches = vlm.match_image_to_candidates(img, candidates)
    assert len(matches.candidates) == 3
    assert matches.candidates[0].text == "red cube"  # index 1 fixed top
    assert matches.candidates[0].rank == 1

    # 4. detect_or_localize_objects
    loc = vlm.detect_or_localize_objects(img, "red cube")
    assert "red cube" in loc.description
    assert len(loc.bboxes) == 1
    assert loc.bboxes[0]["label"] == "red cube"
    assert not loc.validated


def test_vlm_invalid_image_errors():
    vlm = MockVLMAdapter(fail_on_empty_image=True)

    with pytest.raises(InvalidImageError):
        vlm.describe_image(None)

    with pytest.raises(InvalidImageError):
        vlm.describe_image(np.array([]))

    with pytest.raises(InvalidImageError):
        # 1D array is invalid
        vlm.describe_image(np.zeros((50,), dtype=np.uint8))

    with pytest.raises(InvalidImageError):
        # All zeros image with fail_on_empty_image=True
        vlm.describe_image(np.zeros((50, 50, 3), dtype=np.uint8))
