#!/usr/bin/env python3
"""
JARVIS-PiPER: Dataset Converter CLI.
Transcodes raw MCAP demonstration recordings into canonical HDF5 datasets
leveraging the verified SLERP quaternion and linear interpolation engine.
Generates dataset manifest.

Usage:
    python tools/dataset_convert.py /home/humble/pika_mgat_files/episodes/episode_0001.mcap -o /home/humble/pika_mgat_files/hdf5
    python tools/dataset_convert.py /home/humble/pika_mgat_files/episodes/ -o /home/humble/pika_mgat_files/hdf5
"""

import sys
import json
import argparse
from pathlib import Path

# Add pika_mgat_files to sys.path to reuse verified mcap_to_hdf5 engine
PIKA_MGAT_DIR = Path("/home/humble/pika_mgat_files")
if str(PIKA_MGAT_DIR) not in sys.path:
    sys.path.insert(0, str(PIKA_MGAT_DIR))

try:
    from mcap_to_hdf5 import convert
except ImportError as e:
    print(f"[ERROR] Could not import convert from {PIKA_MGAT_DIR}: {e}")
    sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="JARVIS-PiPER MCAP to HDF5 Dataset Converter")
    parser.add_argument("input_path", type=str, help="Path to input .mcap file or directory of .mcap files")
    parser.add_argument("-o", "--output-dir", type=str, required=True, help="Output directory for HDF5 files")
    parser.add_argument("--jpeg", action="store_true", help="Store compressed JPEG bytes in HDF5")
    parser.add_argument("--max-trim", type=float, default=0.20, help="Maximum allowed fraction of trimmed frames")
    parser.add_argument("--manifest", type=str, default="dataset_manifest.json", help="Manifest output filename")
    args = parser.parse_args()

    in_path = Path(args.input_path)
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    if in_path.is_file():
        mcap_files = [in_path]
    elif in_path.is_dir():
        mcap_files = sorted(list(in_path.glob("*.mcap")))
    else:
        print(f"[ERROR] Input path does not exist: {in_path}")
        sys.exit(1)

    print(f"Found {len(mcap_files)} MCAP recordings to process.")
    manifest = []

    for f in mcap_files:
        print(f"Processing: {f.name} ... ", end="", flush=True)
        try:
            out_file = convert(f, out_dir, store_jpeg=args.jpeg, max_trim=args.max_trim)
            print(f"PASS -> {Path(out_file).name}")
            manifest.append({
                "episode_id": f.stem,
                "source_mcap": str(f.resolve()),
                "converted_hdf5": str(Path(out_file).resolve()),
                "status": "CONVERTED"
            })
        except Exception as e:
            print(f"FAIL ({e})")
            manifest.append({
                "episode_id": f.stem,
                "source_mcap": str(f.resolve()),
                "error": str(e),
                "status": "FAILED"
            })

    manifest_path = out_dir / args.manifest
    with open(manifest_path, "w") as mf:
        json.dump({"total_episodes": len(manifest), "episodes": manifest}, mf, indent=2)
    print(f"\nManifest successfully written to: {manifest_path}")


if __name__ == "__main__":
    main()
