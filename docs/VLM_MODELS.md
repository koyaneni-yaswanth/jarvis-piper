# JARVIS-PiPER: VLM Models Reference

**Status:** Phase B — CLIP and BLIP adapters implemented. Moondream and LLaVA deferred.  
**Last updated:** 2026-10-15  

---

## 1. Model Selection Rationale

The Intel NUC 14 has **no NVIDIA discrete GPU** (only Intel Arc integrated graphics).  
All models must either:
- Run on CPU with acceptable latency for perception tasks, or
- Use Intel Arc via OpenVINO (future work, not yet implemented).

> **Rule:** Do not download models automatically. Pre-download to cache. CI runs on `MockVLMAdapter` only.

---

## 2. Model Registry

| Key | Model ID | Size | Tasks | CPU Latency | GPU Latency | Min RAM | CUDA | Notes |
|-----|----------|------|-------|-------------|-------------|---------|------|-------|
| `mock` | mock-vlm | 0 MB | all | <1 ms | — | 0.1 GB | No | CI / MOCK mode only |
| `clip-vit-b32` | openai/clip-vit-base-patch32 | ~338 MB | matching | 200–500 ms | 10–30 ms | 2 GB | No | **Best NUC 14 option for candidate ranking** |
| `blip-base` | Salesforce/blip-image-captioning-base | ~990 MB | captioning, VQA | 2–8 s | 80–200 ms | 4 GB | No | Practical captioning on NUC 14 CPU |
| `blip-large` | Salesforce/blip-image-captioning-large | ~1800 MB | captioning, VQA | 5–15 s | 200–500 ms | 8 GB | No | Better quality, slower |
| `moondream2` | vikhyatk/moondream2 | ~1800 MB | captioning, VQA, localization | 3–10 s | 100–300 ms | 6 GB | No | **Recommended stronger VLM — adapter not yet implemented** |
| `llava-1.5-7b` | liuhaotian/llava-v1.5-7b | ~14 GB | captioning, VQA, instruction | >60 s | 500–2000 ms | 16 GB | ≥12 GB VRAM | **Requires dedicated GPU — deferred** |

---

## 3. Task-to-Model Mapping

| Task | Recommended Model | Notes |
|------|-------------------|-------|
| Scene description | BLIP-base | Captioning model |
| Visual question answering | BLIP-base VQA | Open-ended answers |
| Text-image candidate ranking | CLIP ViT-B/32 | Scores are cosine similarities, NOT probabilities |
| Object localization (coarse) | MockVLMAdapter (CI) / Moondream2 (future) | BLIP/CLIP cannot produce reliable bounding boxes |
| Instruction following | LLaVA-1.5-7B (deferred — needs GPU) | Not available on NUC 14 without eGPU |

---

## 4. Critical Limitations

### 4.1 CLIP Scores Are NOT Probabilities

```python
# CORRECT interpretation:
resp = clip.match_image_to_candidates(image, candidates)
best = resp.candidates[0]  # Highest cosine similarity
# best.score is a cosine similarity in [-1, 1]
# A score of 0.85 does NOT mean 85% probability the object is present

# WRONG (do not do this):
# if best.score > 0.5:
#     robot.go_to(target_pos)  # ← NEVER based on VLM score alone
```

### 4.2 BLIP Cannot Produce Bounding Boxes

BLIP generates natural-language scene descriptions. It does **not** output pixel-level bounding boxes or spatial coordinates. Use `JarvisPerceptionDetector` (YOLO-based) for actual object localization with depth integration.

### 4.3 VLM Output Is Untrusted Perception

VLM descriptions, scores, and proposed locations must be validated by the Safety Supervisor before any robot action. The VLM is in the *perception* layer, not the *command* layer.

```
Camera → VLM → TaskPlanner → SafetySupervisor → HardwareAdapter → Robot
                                    ↑
                            Independent gate — VLM cannot bypass this
```

---

## 5. Pre-Downloading Model Weights (NUC Instructions)

> Do this on the NUC with internet access before any offline deployment.

```bash
# Activate the project venv
cd ~/robotics/jarvis-piper
source .venv/bin/activate
pip install transformers pillow accelerate

# Download CLIP (~338 MB)
python -c "
from transformers import CLIPModel, CLIPProcessor
CLIPModel.from_pretrained('openai/clip-vit-base-patch32')
CLIPProcessor.from_pretrained('openai/clip-vit-base-patch32')
print('CLIP downloaded.')
"

# Download BLIP-base caption (~990 MB)
python -c "
from transformers import BlipForConditionalGeneration, BlipProcessor
BlipProcessor.from_pretrained('Salesforce/blip-image-captioning-base')
BlipForConditionalGeneration.from_pretrained('Salesforce/blip-image-captioning-base')
print('BLIP caption downloaded.')
"

# Download BLIP-base VQA (~990 MB)
python -c "
from transformers import BlipForQuestionAnswering, BlipProcessor
BlipProcessor.from_pretrained('Salesforce/blip-vqa-base')
BlipForQuestionAnswering.from_pretrained('Salesforce/blip-vqa-base')
print('BLIP VQA downloaded.')
"
```

Cache location: `~/.cache/huggingface/hub/`

---

## 6. Moondream2 — Recommended Stronger VLM (Deferred)

**Status:** Deferred. Adapter not yet implemented.  
**Why deferred:** The adapter requires integration with the `moondream` Python package or the HuggingFace `transformers` AutoModel API for moondream2. Both are straightforward but need testing on NUC 14 CPU.

**Why recommended:**
- Runs on CPU (3–10 s per image)
- Supports object localization with coarse bounding boxes
- 1.8 GB — fits NUC 14 RAM budget
- Apache 2.0 license
- Actively maintained (2024–2025)

**To implement:** Create `python/jarvis_piper/perception/vlm_moondream.py` following the `VisionLanguageModel` abstract interface pattern.

---

## 7. LLaVA-1.5-7B — Deferred (GPU Required)

**Status:** Deferred until eGPU or Jetson AGX Orin is available.  
**Reason:** Requires ≥12 GB VRAM. NUC 14 has only Intel Arc iGPU with shared memory.  
**Alternative:** Use Moondream2 on CPU for instruction-following tasks at reduced quality.

---

## 8. Never Do This

```python
# 1. Never auto-download weights in production code
blip = BLIPAdapter(download_if_missing=True)  # ← OK for setup, not for production

# 2. Never skip the safety supervisor based on VLM output
if vlm_says_pick_up:
    arm.execute_joint_command(...)  # ← PROHIBITED

# 3. Never use CLIP similarity as a detection threshold for robot actions
if clip_score > 0.7:
    robot.go_to(coords)  # ← PROHIBITED: scores are not probabilities

# 4. Never send user camera images to remote services without consent
vlm = RemoteVLM(api_key="...")  # ← Requires explicit config + consent
```
