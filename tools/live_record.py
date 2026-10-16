#!/usr/bin/env python3
"""
JARVIS-PiPER: Live Hardware Observation Recording CLI.
Records live synchronized telemetry from actual NUC hardware:
- PiPER 6-DOF Arm CAN telemetry (passive read, motors unenabled)
- RealSense D405 (Color & Depth)
- DECXIN overhead camera
- PIKA Sense & Vive Tracker

Usage:
    python tools/live_record.py --duration 10 --task "Initial live observation benchmark"
"""

import sys
import os
import argparse
from pathlib import Path

# Ensure repo root is on sys.path
_repo_dir = str(Path(__file__).resolve().parent.parent)
if _repo_dir not in sys.path:
    sys.path.insert(0, _repo_dir)

from jarvis.live_recorder import LiveObservationRecorder


def main():
    parser = argparse.ArgumentParser(description="JARVIS-PiPER Live Hardware Observation Recorder")
    parser.add_argument("--duration", type=float, default=10.0, help="Recording duration in seconds (default: 10.0s)")
    parser.add_argument("--hz", type=float, default=30.0, help="Target sampling rate (default: 30.0 Hz)")
    parser.add_argument("--out-dir", type=str, default="data/recordings", help="Output recording root directory")
    parser.add_argument("--task", type=str, default="Baseline hardware observation test", help="Task description")
    parser.add_argument("--can-port", type=str, default="can0", help="SocketCAN interface name")
    parser.add_argument("--camera-index", type=int, default=0, help="Overhead camera /dev/video index")
    parser.add_argument("--no-realsense", action="store_true", help="Disable RealSense stream")
    parser.add_argument("--no-pika", action="store_true", help="Disable PIKA Sense stream")
    args = parser.parse_args()

    print("=" * 80)
    print("      JARVIS-PiPER :: LIVE HARDWARE OBSERVATION RECORDER")
    print("=" * 80)
    print(f" Target Duration : {args.duration:.1f} seconds")
    print(f" Target Rate     : {args.hz:.1f} Hz")
    print(f" Output Folder   : {args.out_dir}")
    print(f" Mode            : STRICTLY PASSIVE / READ-ONLY (No motor enable, no movement)")
    print("=" * 80)

    recorder = LiveObservationRecorder(
        output_dir=args.out_dir,
        can_port=args.can_port,
        realsense_enabled=(not args.no_realsense),
        overhead_camera_index=args.camera_index,
        pika_enabled=(not args.no_pika),
        target_control_hz=args.hz,
    )

    print("\n[INFO] Discovering and connecting to physical hardware...")
    hw_status = recorder.initialize_hardware()
    print(" Hardware Discovery Summary:")
    print(f"  - PiPER Arm CAN Telemetry  : {'ONLINE (can0)' if hw_status['piper_telemetry'] else 'OFFLINE'}")
    print(f"  - RealSense D405 Streaming : {'ONLINE (SN: ' + str(hw_status['realsense_serial']) + ')' if hw_status['realsense_d405'] else 'OFFLINE'}")
    print(f"  - Overhead UVC Camera      : {'ONLINE (/dev/video' + str(args.camera_index) + ')' if hw_status['overhead_camera'] else 'OFFLINE'}")
    print(f"  - PIKA Sense Serial Link   : {'ONLINE' if hw_status['pika_sense'] else 'OFFLINE'}")

    active_streams = [k for k, v in hw_status.items() if v]
    if not active_streams:
        print("\n[ERROR] No active hardware streams detected. Check cables and connections.")
        sys.exit(1)

    print(f"\n[INFO] Starting recording for {args.duration:.1f} seconds. Please wait...")
    session_path = recorder.record_session(
        duration_seconds=args.duration,
        task_description=args.task,
        operator_name=os.environ.get("USER", "operator"),
    )

    print("\n" + "=" * 80)
    print(" [PASS] RECORDING COMPLETE")
    print(f" Saved Session Directory : {session_path.resolve()}")
    print(f" Total Duration          : {recorder.stats['duration_sec']:.2f} s")
    print(f" Robot Telemetry Samples : {recorder.stats['robot_telemetry_samples']}")
    print(f" RealSense Color Frames  : {recorder.stats['realsense_color_frames']}")
    print(f" RealSense Depth Frames  : {recorder.stats['realsense_depth_frames']}")
    print(f" Overhead Color Frames   : {recorder.stats['overhead_color_frames']}")
    print(f" PIKA Samples Captured   : {recorder.stats['pika_samples']}")
    print("=" * 80)
    print("\nNext step: Run validation on this session via:")
    print(f"  python tools/live_validate.py {session_path}")


if __name__ == "__main__":
    main()
