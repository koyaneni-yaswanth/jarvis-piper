"""
JARVIS-PiPER: VLM Factory and Model Evaluator.

Provides:
- build_vlm: factory function to instantiate VLM adapters from config
- VLMEvaluator: hardware profiler that selects the appropriate model tier
- MODEL_REGISTRY: documented model comparison table

Model selection for Intel NUC 14 (no discrete GPU):
------------------------------------------------------
Tier 1 (MOCK mode, CI):      MockVLMAdapter  — no weights, always fast
Tier 2 (CPU offline):        CLIP ViT-B/32   — 338 MB, ~200-500 ms/image on CPU
Tier 3 (CPU offline):        BLIP-base       — 990 MB, ~2-8 s/image on CPU
Tier 4 (GPU or future):      LLaVA-1.5-7B   — 14 GB, requires ≥12 GB VRAM

The NUC 14 has Intel Arc iGPU but no NVIDIA CUDA. BLIP and CLIP
support CPU-only inference. LLaVA requires dedicated GPU for real-time use.
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Model registry (hardware requirements documented)
# ---------------------------------------------------------------------------

@dataclass
class ModelSpec:
    """Specification and hardware requirements for a VLM checkpoint."""
    model_id: str
    adapter_class: str
    approx_size_mb: float
    tasks: List[str]
    cpu_latency_ms: Optional[str]   # e.g. "2000-8000"
    gpu_latency_ms: Optional[str]   # e.g. "80-200"
    min_ram_gb: float
    min_vram_gb: Optional[float]    # None = no GPU required
    cuda_required: bool
    offline_capable: bool           # True if can run without internet after cache
    notes: str


MODEL_REGISTRY: Dict[str, ModelSpec] = {
    "mock": ModelSpec(
        model_id="mock-vlm",
        adapter_class="MockVLMAdapter",
        approx_size_mb=0,
        tasks=["captioning", "vqa", "matching", "localization"],
        cpu_latency_ms="<1",
        gpu_latency_ms=None,
        min_ram_gb=0.1,
        min_vram_gb=None,
        cuda_required=False,
        offline_capable=True,
        notes="Deterministic synthetic adapter. No weights. CI / MOCK mode only.",
    ),
    "clip-vit-b32": ModelSpec(
        model_id="openai/clip-vit-base-patch32",
        adapter_class="CLIPAdapter",
        approx_size_mb=338,
        tasks=["matching"],
        cpu_latency_ms="200-500",
        gpu_latency_ms="10-30",
        min_ram_gb=2.0,
        min_vram_gb=None,
        cuda_required=False,
        offline_capable=True,
        notes=(
            "Best choice for NUC 14 CPU-only matching. "
            "Scores are cosine similarities, not probabilities. "
            "No bounding boxes. No captioning."
        ),
    ),
    "blip-base": ModelSpec(
        model_id="Salesforce/blip-image-captioning-base",
        adapter_class="BLIPAdapter",
        approx_size_mb=990,
        tasks=["captioning", "vqa"],
        cpu_latency_ms="2000-8000",
        gpu_latency_ms="80-200",
        min_ram_gb=4.0,
        min_vram_gb=None,
        cuda_required=False,
        offline_capable=True,
        notes=(
            "Practical captioning baseline on NUC 14 CPU. "
            "VQA answers may be imprecise for spatial reasoning. "
            "No bounding boxes."
        ),
    ),
    "blip-large": ModelSpec(
        model_id="Salesforce/blip-image-captioning-large",
        adapter_class="BLIPAdapter",
        approx_size_mb=1800,
        tasks=["captioning", "vqa"],
        cpu_latency_ms="5000-15000",
        gpu_latency_ms="200-500",
        min_ram_gb=8.0,
        min_vram_gb=None,
        cuda_required=False,
        offline_capable=True,
        notes="Better quality than blip-base but significantly slower on CPU.",
    ),
    "moondream2": ModelSpec(
        model_id="vikhyatk/moondream2",
        adapter_class="(future) MoondreamAdapter",
        approx_size_mb=1800,
        tasks=["captioning", "vqa", "localization"],
        cpu_latency_ms="3000-10000",
        gpu_latency_ms="100-300",
        min_ram_gb=6.0,
        min_vram_gb=None,
        cuda_required=False,
        offline_capable=True,
        notes=(
            "Strong instruction-following VLM that runs on CPU. "
            "Supports object localization with bounding boxes (rough). "
            "Recommended stronger VLM for NUC 14. "
            "Adapter not yet implemented — deferred (Phase B future work)."
        ),
    ),
    "llava-1.5-7b": ModelSpec(
        model_id="liuhaotian/llava-v1.5-7b",
        adapter_class="(future) LLaVAAdapter",
        approx_size_mb=14000,
        tasks=["captioning", "vqa", "localization", "instruction"],
        cpu_latency_ms="very slow (>60s)",
        gpu_latency_ms="500-2000",
        min_ram_gb=16.0,
        min_vram_gb=12.0,
        cuda_required=True,
        offline_capable=True,
        notes=(
            "Best instruction-following quality but requires dedicated GPU. "
            "Not suitable for NUC 14 without eGPU. "
            "Deferred until hardware upgrade or eGPU is available."
        ),
    ),
}


# ---------------------------------------------------------------------------
# Hardware detector
# ---------------------------------------------------------------------------

@dataclass
class HardwareProfile:
    """Detected compute capabilities of the current host."""
    has_cuda: bool = False
    cuda_device_name: Optional[str] = None
    cuda_vram_gb: Optional[float] = None
    system_ram_gb: float = 0.0
    cpu_model: Optional[str] = None
    recommended_tier: str = "mock"


def detect_hardware() -> HardwareProfile:
    """Non-destructively detect the compute capabilities of the current host."""
    profile = HardwareProfile()

    # System RAM
    try:
        import psutil  # type: ignore[import]
        profile.system_ram_gb = psutil.virtual_memory().total / (1024 ** 3)
    except ImportError:
        try:
            with open("/proc/meminfo") as f:
                for line in f:
                    if "MemTotal" in line:
                        kb = int(line.split()[1])
                        profile.system_ram_gb = kb / (1024 ** 2)
                        break
        except Exception:
            profile.system_ram_gb = 8.0  # Conservative fallback

    # CUDA
    try:
        import torch  # type: ignore[import]
        if torch.cuda.is_available():
            profile.has_cuda = True
            profile.cuda_device_name = torch.cuda.get_device_name(0)
            props = torch.cuda.get_device_properties(0)
            profile.cuda_vram_gb = props.total_memory / (1024 ** 3)
    except ImportError:
        pass

    # CPU model
    try:
        import platform
        profile.cpu_model = platform.processor()
    except Exception:
        pass

    # Recommend tier
    if profile.has_cuda and (profile.cuda_vram_gb or 0) >= 12.0:
        profile.recommended_tier = "llava-1.5-7b"
    elif profile.system_ram_gb >= 6.0:
        profile.recommended_tier = "blip-base"
    elif profile.system_ram_gb >= 2.0:
        profile.recommended_tier = "clip-vit-b32"
    else:
        profile.recommended_tier = "mock"

    logger.info(
        "Hardware profile: RAM=%.1f GB, CUDA=%s (%s %.1f GB), recommended=%s",
        profile.system_ram_gb,
        profile.has_cuda,
        profile.cuda_device_name or "none",
        profile.cuda_vram_gb or 0.0,
        profile.recommended_tier,
    )
    return profile


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def build_vlm(config: Dict[str, Any]) -> "VisionLanguageModel":  # noqa: F821
    """
    Build a VisionLanguageModel from a configuration dictionary.

    Required keys:
    - ``type``: one of "mock", "blip", "clip"
      (LLaVA / Moondream not yet implemented)

    Optional keys:
    - ``model_id``: override the default model checkpoint
    - ``cache_dir``: local weight cache directory
    - ``download_if_missing``: bool (default False)
    - ``timeout_s``: float (default 30.0)
    - ``force_cpu``: bool (default False)

    Examples
    --------
    {"type": "mock"}
    {"type": "clip", "download_if_missing": false}
    {"type": "blip", "model_id": "Salesforce/blip-image-captioning-base", "force_cpu": true}

    Returns
    -------
    VisionLanguageModel
        An unloaded VLM adapter. Call .load() before inference.

    Raises
    ------
    ValueError
        If an unsupported type is requested.
    """
    from jarvis_piper.perception.vlm_interface import VisionLanguageModel
    from jarvis_piper.perception.vlm_mock import MockVLMAdapter
    from jarvis_piper.perception.vlm_blip import BLIPAdapter
    from jarvis_piper.perception.vlm_clip import CLIPAdapter

    vlm_type = config.get("type", "mock").lower()
    cache_dir = config.get("cache_dir", None)
    download = bool(config.get("download_if_missing", False))
    timeout = float(config.get("timeout_s", 30.0))
    force_cpu = bool(config.get("force_cpu", False))

    if vlm_type == "mock":
        return MockVLMAdapter(
            fixed_caption=config.get(
                "fixed_caption",
                "a robotic tabletop with a red block and a bowl",
            ),
            fixed_answer=config.get("fixed_answer", "yes"),
        )

    elif vlm_type == "clip":
        model_id = config.get("model_id", "openai/clip-vit-base-patch32")
        return CLIPAdapter(
            model_id=model_id,
            cache_dir=cache_dir,
            download_if_missing=download,
            timeout_s=timeout,
            force_cpu=force_cpu,
        )

    elif vlm_type == "blip":
        caption_id = config.get(
            "model_id", "Salesforce/blip-image-captioning-base"
        )
        vqa_id = config.get("vqa_model_id", "Salesforce/blip-vqa-base")
        return BLIPAdapter(
            caption_model_id=caption_id,
            vqa_model_id=vqa_id,
            cache_dir=cache_dir,
            download_if_missing=download,
            timeout_s=timeout,
            force_cpu=force_cpu,
        )

    elif vlm_type in ("llava", "moondream"):
        raise ValueError(
            f"VLM type '{vlm_type}' is listed in MODEL_REGISTRY but has not "
            f"yet been implemented. See docs/VLM_MODELS.md for status and "
            f"hardware requirements."
        )

    else:
        raise ValueError(
            f"Unknown VLM type: {vlm_type!r}. "
            f"Supported: 'mock', 'clip', 'blip'. "
            f"See MODEL_REGISTRY for the full list."
        )
