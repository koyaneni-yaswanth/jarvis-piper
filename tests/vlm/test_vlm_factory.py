"""
Tests for VLM Factory, Hardware Profiler, and Model Registry.
"""

import pytest
from jarvis_piper.perception.vlm_factory import (
    build_vlm,
    detect_hardware,
    MODEL_REGISTRY,
    HardwareProfile,
)
from jarvis_piper.perception.vlm_mock import MockVLMAdapter
from jarvis_piper.perception.vlm_interface import ModelUnavailableError


def test_model_registry_integrity():
    assert "mock" in MODEL_REGISTRY
    assert "clip-vit-b32" in MODEL_REGISTRY
    assert "blip-base" in MODEL_REGISTRY

    # Check that each entry has documented specs
    for name, spec in MODEL_REGISTRY.items():
        assert spec.model_id
        assert spec.adapter_class
        assert isinstance(spec.tasks, list)
        assert spec.min_ram_gb >= 0


def test_hardware_detector():
    profile = detect_hardware()
    assert isinstance(profile, HardwareProfile)
    assert profile.system_ram_gb > 0
    assert profile.recommended_tier in MODEL_REGISTRY


def test_build_vlm_mock():
    vlm = build_vlm({"type": "mock", "fixed_caption": "custom caption"})
    assert isinstance(vlm, MockVLMAdapter)
    assert vlm.is_loaded()


def test_build_vlm_unknown_type():
    with pytest.raises(ValueError, match="Unknown VLM type"):
        build_vlm({"type": "non_existent_model_tier"})


def test_build_vlm_future_tier():
    with pytest.raises(ValueError, match="has not yet been implemented"):
        build_vlm({"type": "llava"})
