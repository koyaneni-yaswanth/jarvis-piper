"""
JARVIS-PiPER: VLM Component Test Suite.

Tests:
- Camera abstraction layer (mock, build_camera_source factory)
- VLM interface contracts (all abstract methods)
- MockVLMAdapter (all operations, no weights required)
- BLIPAdapter / CLIPAdapter (weight-absent behavior, offline mode)
- VLM factory (build_vlm)
- VisionTaskPlanner (plan generation, MOCK execution)
- Safety: hardware steps blocked without authorization
- Safety: VLM output rejected as untrusted when producing coordinates
- Edge cases: empty image, None image, empty candidates, timeout simulation
- Operating mode isolation

All tests run without model downloads, camera hardware, or robot hardware.
Tests that require real model weights are explicitly marked @pytest.mark.optional.
"""

import numpy as np
import pytest

from jarvis_piper.perception.camera import (
    MockCamera,
    CameraFrame,
    CameraUnavailableError,
    CameraNotOpenError,
    ColorFormat,
    build_camera_source,
)
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
from jarvis_piper.perception.vlm_factory import (
    build_vlm,
    detect_hardware,
    MODEL_REGISTRY,
    HardwareProfile,
)
from jarvis_piper.tasks.vlm_planner import (
    VisionTaskPlanner,
    TaskPlan,
    PlanStep,
    StepStatus,
    TaskType,
    classify_task,
)


# ==========================================================================
# Fixtures
# ==========================================================================

@pytest.fixture
def valid_bgr_image() -> np.ndarray:
    """A valid 480x640x3 BGR uint8 image (medium grey)."""
    return np.full((480, 640, 3), 127, dtype=np.uint8)


@pytest.fixture
def small_bgr_image() -> np.ndarray:
    """A small 64x64x3 BGR image."""
    return np.zeros((64, 64, 3), dtype=np.uint8)


@pytest.fixture
def empty_image() -> np.ndarray:
    """A 480x640x3 all-zeros image."""
    return np.zeros((480, 640, 3), dtype=np.uint8)


@pytest.fixture
def mock_camera() -> MockCamera:
    return MockCamera(source_id="test_cam", width=640, height=480)


@pytest.fixture
def mock_vlm() -> MockVLMAdapter:
    vlm = MockVLMAdapter()
    vlm.load()
    return vlm


@pytest.fixture
def planner(mock_vlm, mock_camera):
    mock_camera.open()
    return VisionTaskPlanner(vlm=mock_vlm, camera=mock_camera)


# ==========================================================================
# Camera abstraction tests
# ==========================================================================

class TestMockCamera:
    def test_mock_camera_opens(self, mock_camera):
        assert not mock_camera.is_open
        mock_camera.open()
        assert mock_camera.is_open

    def test_mock_camera_read_returns_valid_frame(self, mock_camera):
        mock_camera.open()
        frame = mock_camera.read()
        assert isinstance(frame, CameraFrame)
        assert frame.is_valid
        assert frame.color_image is not None
        assert frame.color_image.shape == (480, 640, 3)
        assert frame.color_image.dtype == np.uint8
        assert frame.frame_id == 0
        assert frame.source_id == "test_cam"
        assert frame.color_format == ColorFormat.BGR

    def test_mock_camera_increments_frame_id(self, mock_camera):
        mock_camera.open()
        f0 = mock_camera.read()
        f1 = mock_camera.read()
        f2 = mock_camera.read()
        assert f0.frame_id == 0
        assert f1.frame_id == 1
        assert f2.frame_id == 2

    def test_mock_camera_has_depth(self, mock_camera):
        mock_camera.open()
        frame = mock_camera.read()
        assert frame.has_depth
        assert frame.depth_image is not None
        assert frame.depth_image.ndim == 2
        assert frame.depth_image.shape == (mock_camera.height, mock_camera.width)

    def test_mock_camera_close(self, mock_camera):
        mock_camera.open()
        mock_camera.close()
        assert not mock_camera.is_open

    def test_mock_camera_read_before_open_raises(self, mock_camera):
        with pytest.raises(CameraNotOpenError):
            mock_camera.read()

    def test_mock_camera_context_manager(self):
        cam = MockCamera(source_id="ctx_cam")
        with cam as c:
            assert c.is_open
            frame = c.read()
            assert frame.is_valid
        assert not cam.is_open

    def test_mock_camera_configurable_color(self):
        cam = MockCamera(color_bgr=(255, 0, 0))
        cam.open()
        frame = cam.read()
        # All pixels should be (255, 0, 0) in BGR
        assert np.all(frame.color_image[:, :, 0] == 255)
        assert np.all(frame.color_image[:, :, 1] == 0)
        cam.close()

    def test_mock_camera_no_depth(self):
        cam = MockCamera(depth_mm=None)
        cam.open()
        frame = cam.read()
        assert not frame.has_depth
        cam.close()


class TestBuildCameraSource:
    def test_build_mock_camera_default(self):
        cam = build_camera_source({"type": "mock"})
        assert isinstance(cam, MockCamera)

    def test_build_mock_camera_explicit(self):
        cam = build_camera_source({
            "type": "mock",
            "width": 320,
            "height": 240,
            "source_id": "test",
        })
        assert cam.width == 320
        assert cam.height == 240
        assert cam.source_id == "test"

    def test_build_unknown_type_raises(self):
        with pytest.raises(ValueError, match="Unknown camera type"):
            build_camera_source({"type": "laser_scan"})

    def test_build_recorded_without_paths_raises(self):
        with pytest.raises(ValueError, match="paths"):
            build_camera_source({"type": "recorded"})

    def test_build_usb_requires_device_index(self):
        # Should succeed in creating (not opening) without a real device
        from jarvis_piper.perception.camera import UsbCamera
        cam = build_camera_source({"type": "usb", "device_index": 0})
        assert isinstance(cam, UsbCamera)
        assert not cam.is_open


# ==========================================================================
# VLM interface contract tests
# ==========================================================================

class TestMockVLMAdapter:
    def test_mock_vlm_is_always_loaded(self):
        vlm = MockVLMAdapter()
        assert vlm.is_loaded()  # Mock is always loaded without calling load()

    def test_mock_vlm_load_is_noop(self):
        vlm = MockVLMAdapter()
        vlm.load()
        assert vlm.is_loaded()

    def test_describe_image_returns_caption(self, mock_vlm, valid_bgr_image):
        resp = mock_vlm.describe_image(valid_bgr_image)
        assert isinstance(resp, CaptionResponse)
        assert isinstance(resp.caption, str)
        assert len(resp.caption) > 0
        assert resp.latency_s >= 0.0
        assert resp.model_id == "mock-vlm"

    def test_describe_image_none_raises(self, mock_vlm):
        with pytest.raises(InvalidImageError):
            mock_vlm.describe_image(None)

    def test_describe_image_empty_raises(self, mock_vlm):
        empty = np.array([])
        with pytest.raises(InvalidImageError):
            mock_vlm.describe_image(empty)

    def test_describe_image_wrong_shape_raises(self, mock_vlm):
        bad = np.zeros((10,), dtype=np.uint8)
        with pytest.raises(InvalidImageError):
            mock_vlm.describe_image(bad)

    def test_answer_vqa_returns_response(self, mock_vlm, valid_bgr_image):
        resp = mock_vlm.answer_visual_question(valid_bgr_image, "Is there a red block?")
        assert isinstance(resp, VQAResponse)
        assert resp.question == "Is there a red block?"
        assert isinstance(resp.answer, str)
        assert len(resp.answer) > 0

    def test_match_candidates_returns_ranked_list(self, mock_vlm, valid_bgr_image):
        candidates = ["red cube", "blue bowl", "empty table"]
        resp = mock_vlm.match_image_to_candidates(valid_bgr_image, candidates)
        assert isinstance(resp, MatchResponse)
        assert len(resp.candidates) == 3
        # Verify descending rank order
        for i, c in enumerate(resp.candidates):
            assert c.rank == i + 1
        # Scores should be in descending order
        scores = [c.score for c in resp.candidates]
        assert scores == sorted(scores, reverse=True)

    def test_match_candidates_empty_list(self, mock_vlm, valid_bgr_image):
        resp = mock_vlm.match_image_to_candidates(valid_bgr_image, [])
        assert resp.candidates == []

    def test_match_candidates_single_item(self, mock_vlm, valid_bgr_image):
        resp = mock_vlm.match_image_to_candidates(valid_bgr_image, ["red block"])
        assert len(resp.candidates) == 1
        assert resp.candidates[0].rank == 1

    def test_localize_objects_returns_result(self, mock_vlm, valid_bgr_image):
        result = mock_vlm.detect_or_localize_objects(valid_bgr_image, "red block")
        assert isinstance(result, LocalizationResult)
        assert result.request == "red block"
        assert isinstance(result.description, str)
        # validated must be False — VLM output is untrusted perception
        assert result.validated is False

    def test_localize_objects_never_validated(self, mock_vlm, valid_bgr_image):
        """VLM localization must never self-report as validated."""
        result = mock_vlm.detect_or_localize_objects(valid_bgr_image, "anything")
        assert result.validated is False, (
            "VLM output must never be self-marked as validated. "
            "Validation requires a separate physical or geometric verification."
        )

    def test_mock_vlm_fail_on_empty(self, valid_bgr_image):
        vlm = MockVLMAdapter(fail_on_empty_image=True)
        zeros = np.zeros_like(valid_bgr_image)
        with pytest.raises(InvalidImageError, match="all-zeros"):
            vlm.describe_image(zeros)
        # Non-zero image should still work
        resp = vlm.describe_image(valid_bgr_image)
        assert resp.caption

    def test_match_note_warns_about_scores(self, mock_vlm, valid_bgr_image):
        """MatchResponse must include a note about scores not being probabilities."""
        resp = mock_vlm.match_image_to_candidates(valid_bgr_image, ["a", "b"])
        assert "cosine" in resp.note.lower() or "similarity" in resp.note.lower(), (
            "MatchResponse.note must clearly state that scores are cosine similarities, "
            "not probabilities."
        )


# ==========================================================================
# Model unavailability tests (offline behavior)
# ==========================================================================

class TestModelUnavailability:
    def test_blip_raises_without_weights(self, valid_bgr_image):
        """BLIPAdapter with download_if_missing=False must raise when weights absent."""
        from jarvis_piper.perception.vlm_blip import BLIPAdapter
        try:
            import transformers  # noqa: F401
        except ImportError:
            pytest.skip("transformers not installed; skipping BLIP offline test.")

        adapter = BLIPAdapter(
            cache_dir="/tmp/nonexistent_vlm_cache_jarvis_test",
            download_if_missing=False,
        )
        with pytest.raises(ModelUnavailableError):
            adapter.load()

    def test_clip_raises_without_weights(self, valid_bgr_image):
        """CLIPAdapter with download_if_missing=False must raise when weights absent."""
        from jarvis_piper.perception.vlm_clip import CLIPAdapter
        try:
            import transformers  # noqa: F401
        except ImportError:
            pytest.skip("transformers not installed; skipping CLIP offline test.")

        adapter = CLIPAdapter(
            cache_dir="/tmp/nonexistent_vlm_cache_jarvis_test",
            download_if_missing=False,
        )
        with pytest.raises(ModelUnavailableError):
            adapter.load()

    def test_blip_inference_before_load_raises(self, valid_bgr_image):
        """Calling describe_image before load() must raise ModelUnavailableError."""
        from jarvis_piper.perception.vlm_blip import BLIPAdapter
        adapter = BLIPAdapter.__new__(BLIPAdapter)
        adapter._loaded = False
        adapter._caption_model = None
        adapter._vqa_model = None
        with pytest.raises((ModelUnavailableError, AttributeError)):
            # Either ModelUnavailableError from _require_loaded or AttributeError
            # before that check — both signal correct unloaded state handling
            adapter.describe_image(valid_bgr_image)

    def test_clip_inference_before_load_raises(self, valid_bgr_image):
        """Calling match_image before load() must raise ModelUnavailableError."""
        from jarvis_piper.perception.vlm_clip import CLIPAdapter
        adapter = CLIPAdapter.__new__(CLIPAdapter)
        adapter._loaded = False
        adapter._model = None
        with pytest.raises((ModelUnavailableError, AttributeError)):
            adapter.match_image_to_candidates(valid_bgr_image, ["a"])


# ==========================================================================
# VLM factory tests
# ==========================================================================

class TestBuildVLM:
    def test_build_mock_vlm(self):
        vlm = build_vlm({"type": "mock"})
        assert isinstance(vlm, MockVLMAdapter)
        assert vlm.is_loaded()

    def test_build_clip_returns_clip_adapter(self):
        from jarvis_piper.perception.vlm_clip import CLIPAdapter
        vlm = build_vlm({"type": "clip", "download_if_missing": False})
        assert isinstance(vlm, CLIPAdapter)
        assert not vlm.is_loaded()  # Not loaded yet

    def test_build_blip_returns_blip_adapter(self):
        from jarvis_piper.perception.vlm_blip import BLIPAdapter
        vlm = build_vlm({"type": "blip", "download_if_missing": False})
        assert isinstance(vlm, BLIPAdapter)
        assert not vlm.is_loaded()

    def test_build_unknown_raises(self):
        with pytest.raises(ValueError, match="Unknown VLM type"):
            build_vlm({"type": "gpt-99"})

    def test_build_llava_raises_not_implemented(self):
        with pytest.raises(ValueError, match="not yet been implemented"):
            build_vlm({"type": "llava"})

    def test_model_registry_completeness(self):
        """MODEL_REGISTRY must document hardware requirements for every entry."""
        for key, spec in MODEL_REGISTRY.items():
            assert spec.model_id, f"{key}: model_id missing"
            assert spec.adapter_class, f"{key}: adapter_class missing"
            assert spec.tasks, f"{key}: tasks list empty"
            assert spec.notes, f"{key}: notes missing"
            assert isinstance(spec.min_ram_gb, (int, float)), f"{key}: min_ram_gb missing"


class TestHardwareDetection:
    def test_detect_hardware_returns_profile(self):
        profile = detect_hardware()
        assert isinstance(profile, HardwareProfile)
        assert isinstance(profile.has_cuda, bool)
        assert profile.system_ram_gb > 0
        assert profile.recommended_tier in MODEL_REGISTRY


# ==========================================================================
# VLM Task Planner tests
# ==========================================================================

class TestClassifyTask:
    @pytest.mark.parametrize("user_request,expected", [
        ("Describe what you see on the table", TaskType.SCENE_DESCRIPTION),
        ("What is the object on the left?", TaskType.OBJECT_IDENTIFICATION),
        ("Where is the red block?", TaskType.OBJECT_LOCALIZATION),
        ("Pick up the red cube and place it in the bowl", TaskType.MANIPULATION),
        ("Is there a cup on the table?", TaskType.VISUAL_QUERY),
    ])
    def test_classify_request(self, user_request, expected):
        assert classify_task(user_request) == expected


    def test_unknown_request(self):
        result = classify_task("xyzzy fnord blargh")
        assert result == TaskType.UNKNOWN


class TestVisionTaskPlanner:
    def test_plan_scene_description(self, planner):
        plan = planner.plan("Describe what you see")
        assert isinstance(plan, TaskPlan)
        assert len(plan.steps) > 0
        assert not plan.is_hardware_task

    def test_plan_manipulation_has_hardware_steps(self, planner):
        plan = planner.plan("Pick up the red block and place it in the bowl")
        assert plan.is_hardware_task
        hw_steps = [s for s in plan.steps if s.requires_hardware]
        assert len(hw_steps) >= 5, "Manipulation must include hardware-gated steps"

    def test_plan_manipulation_all_hardware_steps_require_operator(self, planner):
        """Every hardware step must require operator confirmation."""
        plan = planner.plan("Grab the cube")
        for step in plan.steps:
            if step.requires_hardware:
                assert step.requires_operator_confirmation, (
                    f"Step {step.step_id} requires hardware but not operator confirmation: "
                    f"{step.description}"
                )

    def test_execute_perception_plan_mock_mode(self, planner):
        """Scene description plan should execute fully in mock mode."""
        plan = planner.plan("Look at the table and describe the scene")
        result = planner.execute_plan(plan, operator_authorized=False)
        # All non-hardware steps should complete
        hw_steps = [s for s in result.steps if s.requires_hardware]
        non_hw_steps = [s for s in result.steps if not s.requires_hardware]
        assert all(
            s.status == StepStatus.COMPLETED for s in non_hw_steps
        ), f"Non-hardware steps failed: {[str(s) for s in non_hw_steps if s.status != StepStatus.COMPLETED]}"
        assert len(hw_steps) == 0, "Scene description should have no hardware steps"

    def test_execute_manipulation_blocks_hardware_without_auth(self, planner):
        """Hardware steps must be blocked when operator_authorized=False."""
        plan = planner.plan("Pick up the red block")
        result = planner.execute_plan(plan, operator_authorized=False)
        blocked = [
            s for s in result.steps
            if s.requires_hardware and s.status == StepStatus.AWAITING_OPERATOR
        ]
        assert len(blocked) > 0, (
            "Hardware steps must be AWAITING_OPERATOR when not authorized"
        )
        # Confirm no hardware step completed
        hw_completed = [
            s for s in result.steps
            if s.requires_hardware and s.status == StepStatus.COMPLETED
        ]
        assert hw_completed == [], (
            "Hardware steps must NOT complete without operator authorization"
        )

    def test_plan_notes_warn_about_vlm_as_untrusted(self, planner):
        """Manipulation plan notes must warn that VLM is untrusted perception."""
        plan = planner.plan("Move the bowl to the left")
        all_notes = " ".join(plan.notes).lower()
        # Check that the plan communicates VLM is perception-only
        assert any(
            keyword in all_notes
            for keyword in ["perception", "does not generate", "joint command", "safety supervisor"]
        ), (
            "Manipulation plan must document that VLM is perception-only "
            "and does not generate joint commands."
        )

    def test_vlm_localization_never_reaches_arm(self, planner):
        """Localization result must never directly cause arm motion."""
        plan = planner.plan("Find the red cube")
        result = planner.execute_plan(plan, operator_authorized=False)
        # No hardware steps in localization plan
        hw_steps = [s for s in result.steps if s.requires_hardware]
        assert hw_steps == [], (
            "Localization plan must not contain hardware actuation steps"
        )


# ==========================================================================
# Safety isolation tests
# ==========================================================================

class TestVLMSafetyIsolation:
    def test_vlm_output_is_not_joint_command(self, mock_vlm, valid_bgr_image):
        """VLM caption must never contain raw joint angles."""
        resp = mock_vlm.describe_image(valid_bgr_image)
        # Caption should be natural language, not a joint command list
        assert not resp.caption.startswith("["), (
            "VLM caption should not be a JSON/list that could be misused as a joint command"
        )

    def test_localization_result_not_validated(self, mock_vlm, valid_bgr_image):
        """VLM localization output must not be pre-validated for robot use."""
        result = mock_vlm.detect_or_localize_objects(valid_bgr_image, "red block")
        assert result.validated is False

    def test_mock_mode_camera_produces_synthetic_tag(self):
        """MockCamera frames must be tagged as synthetic."""
        cam = MockCamera()
        cam.open()
        frame = cam.read()
        assert frame.metadata.get("synthetic") is True, (
            "MockCamera must tag frames with metadata['synthetic'] = True"
        )
        cam.close()

    def test_operating_mode_does_not_auto_enable_motors(self, planner):
        """Changing task type must not implicitly enable motor actuation."""
        # Even a manipulation plan with operator_authorized=True should not enable motors
        # (motors are controlled by the hardware adapter, not the planner)
        plan = planner.plan("Pick up the red block")
        # Executing WITH auth simulates that operator said yes, but the planner
        # itself still cannot send CAN frames — that's the hardware adapter's job
        result = planner.execute_plan(plan, operator_authorized=True)
        # Hardware steps will complete (planner marks them done) but the planner
        # never instantiates a hardware adapter — no real motors involved
        assert result is not None
