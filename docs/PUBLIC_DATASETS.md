# Public Datasets Usage & Download Guide

This guide details how to ingest verified public demonstration datasets to accelerate pretraining, representation learning, and benchmark evaluation for JARVIS-PiPER.

---

## 1. Quick Ingestion: Download Verified Sample

A lightweight, checksum-verified demonstration sample ($< 50$ MB) can be fetched with a single command:

```bash
python scripts/download_public_dataset_sample.py --dataset lerobot_aloha_sample --output dataset/public/
```

### Expected Output Structure:
```
dataset/public/
└── lerobot_aloha_sample/
    ├── meta/
    │   ├── info.json
    │   ├── episodes.jsonl
    │   └── tasks.jsonl
    ├── data/
    │   └── chunk-000/
    │       └── episode_000000.json
    └── manifest.json
```

---

## 2. Using Public Datasets with JARVIS-PiPER

### Ingesting into Universal Pipeline
Once downloaded, convert or validate any external dataset with:

```bash
# Validate schema and action alignment
jarvis-piper validate --dataset dataset/public/lerobot_aloha_sample/

# Train V-JEPA visual encoder on external frames
jarvis-piper train --config configs/vjepa.yaml --dataset dataset/public/lerobot_aloha_sample/
```

### Policy Pretraining Workflow
```
[ Public Datasets (OXE / DROID) ]
               │
               ▼
   [ Visual Pretraining (V-JEPA) ]
               │
               ▼
[ 50+ Real PIKA Sense + Piper Demos ]
               │
               ▼
 [ Fine-Tuned ACT / Diffusion Policy ]
               │
               ▼
    [ Physical Robot Execution ]
```

---

## 3. Strict Embodiment Isolation Rules

> [!WARNING]
> **Action Space Contamination:** Never directly copy action vectors from Franka (7-DOF), UR5, or bimanual ALOHA robots to the physical AgileX PiPER 6-DOF arm without coordinate re-targeting.
>
> 1. Datasets marked `PRETRAINING_ONLY` (OXE, DROID) should **only** be used for visual encoder pretraining or V-JEPA world modeling.
> 2. Datasets marked `CONVERTIBLE_WITH_VALIDATION` (ALOHA, LeRobot) must be passed through the `UniversalExporter` to remap joint indices $q_1..q_6$ and parallel gripper stroke.
