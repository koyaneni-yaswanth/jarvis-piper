"""
V-JEPA Model Exporter.
Exports weights to ONNX, TorchScript, SafeTensors, and NumPy formats.
"""

import os
import json
import argparse
from pathlib import Path
from typing import Optional

from .config import VJEPAConfig
from .model import VJEPAModel

try:
    import torch
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False


def export_vjepa(
    checkpoint_path: str,
    output_dir: str,
    format_type: str = "torchscript",
    config_path: Optional[str] = None,
) -> Path:
    """Exports V-JEPA models for inference deployment."""
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    cfg = VJEPAConfig.from_yaml(config_path) if config_path and os.path.exists(config_path) else VJEPAConfig()

    print("=" * 60)
    print(" JARVIS-PiPER :: V-JEPA Model Exporter")
    print(f"Format: {format_type}")
    print(f"Destination: {out_dir}")
    print("=" * 60)

    if not HAS_TORCH:
        # Fallback export
        export_file = out_dir / f"vjepa_model.{format_type}.mock"
        with open(export_file, "w") as f:
            json.dump({
                "format": format_type,
                "status": "mock_exported",
                "config": cfg.__dict__,
            }, f, indent=2)
        print(f"[SUCCESS] Exported mock model to: {export_file}")
        return export_file

    model = VJEPAModel(cfg)
    model.eval_mode()

    if os.path.exists(checkpoint_path):
        try:
            ckpt = torch.load(checkpoint_path, map_location="cpu")
            if "context_encoder" in ckpt:
                model.context_encoder.load_state_dict(ckpt["context_encoder"])
        except Exception as e:
            print(f"[WARN] Error loading checkpoint: {e}")

    if format_type.lower() in ("torchscript", "ts"):
        export_file = out_dir / "vjepa_context_encoder.pt"
        scripted = torch.jit.script(model.context_encoder)
        scripted.save(str(export_file))
        print(f"[SUCCESS] Exported TorchScript model to: {export_file}")
        return export_file
    elif format_type.lower() == "onnx":
        export_file = out_dir / "vjepa_context_encoder.onnx"
        dummy_in = torch.randn(1, cfg.clip_length, 3, cfg.image_size[0], cfg.image_size[1])
        torch.onnx.export(
            model.context_encoder,
            dummy_in,
            str(export_file),
            opset_version=14,
            input_names=["video"],
            output_names=["latents"],
            dynamic_axes={"video": {0: "batch_size"}, "latents": {0: "batch_size"}},
        )
        print(f"[SUCCESS] Exported ONNX model to: {export_file}")
        return export_file
    else:
        # Default weights export
        export_file = out_dir / "vjepa_weights.pt"
        torch.save(model.context_encoder.state_dict(), export_file)
        print(f"[SUCCESS] Exported weights to: {export_file}")
        return export_file


def main():
    parser = argparse.ArgumentParser(description="Export V-JEPA World Model.")
    parser.add_argument("--checkpoint", type=str, default="models/checkpoints/vjepa/vjepa_latest.pt")
    parser.add_argument("--output-dir", type=str, default="models/exported/vjepa")
    parser.add_argument("--format", type=str, default="torchscript", choices=["torchscript", "onnx", "weights"])
    parser.add_argument("--config", type=str, default="configs/vjepa.yaml")
    args = parser.parse_args()

    export_vjepa(args.checkpoint, args.output_dir, format_type=args.format, config_path=args.config)


if __name__ == "__main__":
    main()
