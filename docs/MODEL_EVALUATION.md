# JARVIS-PiPER: Model Evaluation, Benchmarking, and Hardware Profiles

**Status:** Complete  
**Date:** 2026-10-15  
**Audience:** Robotics AI Engineers, MLOps, System Architects  

---

## 1. Executive Summary

JARVIS-PiPER integrates multimodal vision-language intelligence into an embodied manipulation framework while strictly adhering to real-time safety invariants. Because the target physical controller is an **Intel NUC 14 (`humble-NUC14RVS-B`)** with an Intel Core Ultra 5 125H processor and Intel Arc integrated graphics (no discrete NVIDIA CUDA GPU), model architectures must be evaluated specifically for CPU/OpenVINO inference latency, working memory overhead, and functional reliability.

---

## 2. Hardware Architecture & Constraints

| Parameter | Development Host (Windows 11) | Physical Target (Intel NUC 14) |
|---|---|---|
| **CPU** | AMD64 / Multi-core | Intel Core Ultra 5 125H (14 cores / 18 threads) |
| **System RAM** | 32 GB DDR5 | 32 GB DDR5 |
| **GPU / Acceleration** | NVIDIA GeForce RTX 5060 Laptop (CUDA 12.x) | Intel Arc Graphics (OpenVINO / CPU execution) |
| **CUDA Available** | Yes | **No** (Torch runs on CPU fallback) |
| **Operating System** | Windows 11 Pro | Ubuntu 22.04.5 LTS |
| **ROS Distro** | N/A | ROS 2 Humble Hawksbill |
| **CAN Bus Interface** | Mock / Emulated | SocketCAN (`can0` @ 1 Mbps) |

---

## 3. Evaluated Model Tiers

```
+---------------------------------------------------------------------------------------+
|                                    JARVIS-PiPER VLM Tiers                             |
+---------------------------------------------------------------------------------------+
| Tier 1: MOCK        | MockVLMAdapter     | 0 MB   | Latency: <1 ms      | CI, Unit Tests |
| Tier 2: CPU Fast    | CLIP ViT-B/32      | 338 MB | Latency: 200-500 ms | Text Matching  |
| Tier 3: CPU Medium  | BLIP-Base          | 990 MB | Latency: 2-8 s      | Captioning,VQA |
| Tier 4: Edge GPU    | Moondream2 (Future)| 1.8 GB | Latency: 100-300 ms | Grounding      |
| Tier 5: High Compute| LLaVA-1.5-7B (Def) | 14 GB  | Latency: >60 s CPU  | Deferred       |
+---------------------------------------------------------------------------------------+
```

### 3.1 Tier 1: Mock Adapter (`MockVLMAdapter`)
- **Memory Footprint:** 0 MB weights.
- **Inference Latency:** < 1 ms.
- **Network Dependency:** None (100% offline).
- **Intended Role:** Continuous integration, mock hardware simulation, deterministic unit testing.

### 3.2 Tier 2: CLIP ViT-B/32 (`CLIPAdapter`)
- **Model Checkpoint:** `openai/clip-vit-base-patch32` (~338 MB).
- **Hardware Profile:** Runs comfortably on Intel Core Ultra CPU in 200–500 ms.
- **Role:** Candidate hypothesis ranking via normalized cosine similarity.
- **Safety Critical Evaluation:**
  - CLIP outputs are cosine similarities in $[-1, 1]$, *not* calibrated probabilities.
  - Scores must never be treated as existence proofs for physical grasping without spatial verification.

### 3.3 Tier 3: BLIP-Base (`BLIPAdapter`)
- **Model Checkpoints:** `Salesforce/blip-image-captioning-base` (~990 MB), `Salesforce/blip-vqa-base`.
- **Hardware Profile:** 2–8 seconds on NUC CPU; requires ~4 GB system RAM.
- **Role:** Natural language scene descriptions and interactive VQA for operator confirmation.
- **Safety Critical Evaluation:**
  - BLIP is an ungrounded language generator.
  - It does *not* produce Cartesian coordinates or 3D bounding boxes.
  - Pixel deprojection must be delegated to `JarvisPerceptionDetector` or RGB-D sensors.

### 3.4 Tier 4: Lightweight Instruction VLMs (e.g., Moondream2)
- **Model Checkpoint:** `vikhyatk/moondream2` (~1.8 GB).
- **Target Latency:** 3–10 s on CPU; supports rudimentary bounding box prompts.
- **Status:** Architecture interface prepared; full adapter integration scheduled for Phase B.

### 3.5 Tier 5: Large Vision-Language Models (e.g., LLaVA-1.5-7B)
- **Status:** **DEFERRED**.
- **Rationale:** Requires $\ge 12$ GB VRAM for real-time inference. On NUC 14 CPU, token generation exceeds 60 seconds per prompt, making it unusable for closed-loop robotics.

---

## 4. Empirical Evaluation Protocol

All models are evaluated on four distinct capabilities:
1. `describe_image(image: np.ndarray) -> CaptionResponse`
2. `answer_visual_question(image: np.ndarray, question: str) -> VQAResponse`
3. `match_image_to_candidates(image: np.ndarray, candidates: List[str]) -> MatchResponse`
4. `detect_or_localize_objects(image: np.ndarray, request: str) -> LocalizationResult`

### Automated Hardware Profiler
The framework includes an automated hardware profiler accessible via CLI:
```bash
python -m jarvis.cli vlm --evaluate
```
This inspects system RAM, CPU topology, and CUDA availability to recommend the optimal operational tier dynamically.
