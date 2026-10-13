"""
Unit tests for Phase 4: V-JEPA Integration Modules:
- Module A: Visual representation extraction (VJEPAVisualEncoder)
- Module B: Temporal prediction evaluation (TemporalPredictorEvaluator)
- Module C: Action-conditioned world-model rollouts (VJEPAActionConditionedModel)
"""

import numpy as np
import pytest
from vjepa.encoder.vjepa_encoder import VJEPAVisualEncoder
from vjepa.prediction.temporal_predictor import TemporalPredictorEvaluator
from vjepa.action_conditioned.vjepa_ac import VJEPAActionConditionedModel


def test_vjepa_visual_encoder_smoke():
    encoder = VJEPAVisualEncoder()
    dummy_video = np.random.randint(0, 255, (8, 240, 320, 3), dtype=np.uint8)

    emb = encoder.extract_embedding(dummy_video)
    assert emb.ndim == 1
    assert len(emb) == encoder.config.embed_dim
    assert not np.isnan(emb).any()


def test_vjepa_temporal_predictor_eval():
    evaluator = TemporalPredictorEvaluator()
    v0 = np.random.randint(0, 255, (8, 240, 320, 3), dtype=np.uint8)
    v1 = np.random.randint(0, 255, (8, 240, 320, 3), dtype=np.uint8)

    res = evaluator.evaluate_temporal_consistency(v0, v1)
    assert "prediction_l1_error" in res
    assert "latent_cosine_similarity" in res
    assert "identity_baseline_l1" in res
    assert res["collapse_prevented"] is True


def test_vjepa_action_conditioned_rollout():
    model = VJEPAActionConditionedModel()
    dummy_video = np.random.randint(0, 255, (8, 240, 320, 3), dtype=np.uint8)
    actions = [[0.1 * i] * 6 + [0.035] for i in range(4)]

    latents = model.rollout_latent_trajectory(dummy_video, actions)
    assert len(latents) == 4
    for z in latents:
        assert len(z) == model.config.embed_dim
        assert not np.isnan(z).any()
