# Research Roadmap: Towards JARVIS Embodied Intelligence

The ultimate vision of the JARVIS-PiPER project is to evolve from high-fidelity teleoperation data collection into an autonomous, closed-loop embodied intelligence system capable of multi-step manipulation, spatial reasoning, and continuous self-supervised learning.

---

## 1. Phase 1: Robust Data Collection Foundation (Complete)
- [x] Hardware abstraction layer supporting real PiPER arm and PIKA Sense controller.
- [x] Zero-hardware mock mode and synthetic episode generator.
- [x] Sub-millisecond multi-rate time synchronizer with adaptive slop matching.
- [x] Append-only crash-proof stream journal (`stream_journal.jsonl`).
- [x] Universal dataset exporters (LeRobot v2.0, ALOHA HDF5, RLDS).
- [x] V-JEPA visual world model architecture with EMA target encoder and latent predictor.

---

## 2. Phase 2: Foundation Representation Learning (Current)
- [ ] Large-scale V-JEPA pretraining across 100+ hours of dexterous manipulation episodes.
- [ ] Integration of 3D spatial representations (SE(3) point clouds, depth tokenization).
- [ ] Contrastive action-conditioned latent rollout objectives for causal dynamics prediction.
- [ ] Representation probing on task-phase identification and affordance segmentation.

---

## 3. Phase 3: Vision-Language-Action (VLA) Policy Learning
- [ ] Downstream policy fine-tuning using Action Chunking with Transformers (ACT) and Diffusion Policies.
- [ ] Multimodal language grounding (Open-Vocabulary instructions via CLIP / PaliGemma / Open-X).
- [ ] Model-Predictive Control (MPC) trajectory planning guided by latent V-JEPA rollouts.

---

## 4. Phase 4: Full Autonomous JARVIS Embodied System
- [ ] Autonomous error recovery: world model detects deviation between predicted state and actual observation, triggering corrective grasps.
- [ ] Self-improving fleet learning: continuous telemetry streaming to cloud training pipelines.
- [ ] Seamless integration with mobile manipulators (e.g. AgileX Ranger Mini + PiPER dual-arm mobile platforms).
