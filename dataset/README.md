# JARVIS-PiPER Dataset Directory

This directory hosts demonstration episodes collected from the AgileX PiPER robot and PIKA Sense teleoperation system.

---

## Directory Organization

```
dataset/
├── raw/                 # Raw recorded demonstration episodes
│   ├── ep_demo_001_.../
│   │   ├── metadata.json
│   │   ├── trajectory.json
│   │   ├── stream_journal.jsonl
│   │   └── camera_wrist.mp4
├── exports/             # Standardized format exports
│   ├── lerobot_v2/      # Hugging Face LeRobot format
│   ├── aloha_hdf5/      # ALOHA / ACT HDF5 or NPZ format
│   └── rlds/            # Open X-Embodiment RLDS format
```

---

## Dataset Operations

- **Generate Mock Episodes**:
  ```bash
  jarvis-piper demo --episodes 5 --steps 120
  ```
- **Audit Dataset Quality**:
  ```bash
  jarvis-piper validate --dataset dataset/raw
  ```
- **Export to Universal Formats**:
  ```bash
  jarvis-piper export --format all
  ```
- **Dataset Statistics**:
  ```bash
  jarvis-piper dataset --dataset-dir dataset/raw
  ```
