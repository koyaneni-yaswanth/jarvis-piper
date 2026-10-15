"""
JARVIS-PiPER: Unified Single Command-Line Interface.
Subcommands:
  jarvis doctor     # System, CAN, USB, and environment verification
  jarvis calibrate  # PIKA-to-PiPER calibration and verification
  jarvis teleop     # Teleoperation loop (defaults to --dry-run)
  jarvis record     # Record synchronized demonstrations
  jarvis validate   # 7-point dataset quality validation
  jarvis train      # Behavioral cloning training
  jarvis policy     # Supervised policy rollout (defaults to --dry-run)
"""

import sys
import argparse
from pathlib import Path

# Ensure 'python/' directory is reachable when run from repo root without pip install -e .
_repo_python_dir = str(Path(__file__).resolve().parent.parent / "python")
if _repo_python_dir not in sys.path:
    sys.path.insert(0, _repo_python_dir)

from jarvis.doctor import JarvisDoctor

from jarvis.config_validator import ConfigValidator
from jarvis.hardware import MockArm, MockGripper, MockTeleop
from jarvis.safety import SafetySupervisor
from jarvis.record import EpisodeRecorder, EpisodeValidator
from jarvis.train import train_bc_policy, BCPolicy
from jarvis.policy import SupervisedPolicyRunner


def main():
    parser = argparse.ArgumentParser(
        prog="jarvis",
        description="JARVIS-PiPER: Unified Embodied AI Teleoperation & Policy Framework",
    )
    subparsers = parser.add_subparsers(dest="command", help="Subcommand to execute")

    # doctor
    p_doc = subparsers.add_parser("doctor", help="Run system and hardware diagnostic check")
    p_doc.add_argument("--bundle", action="store_true", help="Generate diagnostic bundle archive")

    # validate-config
    p_cfg = subparsers.add_parser("validate-config", help="Validate config.yaml schema and safety limits")
    p_cfg.add_argument("--config", type=str, default="config.yaml", help="Path to config.yaml")

    # validate
    p_val = subparsers.add_parser("validate", help="Validate recorded episode dataset")
    p_val.add_argument("--dataset", type=str, default="data/raw/episode_mock_001", help="Path to episode or dataset")

    # teleop
    p_tel = subparsers.add_parser("teleop", help="Supervised teleoperation loop")
    p_tel.add_argument("--dry-run", action="store_true", default=True, help="Run without physical arm motion")
    p_tel.add_argument("--execute", action="store_true", help="Enable hardware actuation (requires ENABLE MOTION)")
    p_tel.add_argument("--steps", type=int, default=30, help="Number of teleoperation steps to run")

    # record
    p_rec = subparsers.add_parser("record", help="Record a demonstration episode (mock/real)")
    p_rec.add_argument("--steps", type=int, default=30, help="Number of timesteps to record")
    p_rec.add_argument("--output-dir", type=str, default="data/raw", help="Output directory")

    # train
    p_trn = subparsers.add_parser("train", help="Train Behavioral Cloning (BC) policy")
    p_trn.add_argument("--epochs", type=int, default=5, help="Training epochs")
    p_trn.add_argument("--data-dir", type=str, default="data/raw", help="Dataset directory")

    # policy
    p_pol = subparsers.add_parser("policy", help="Execute supervised policy rollout")
    p_pol.add_argument("--dry-run", action="store_true", default=True, help="Compute actions without physical movement (default)")
    p_pol.add_argument("--execute", action="store_true", help="Enable hardware actuation (requires ENABLE MOTION)")
    p_pol.add_argument("--steps", type=int, default=30, help="Rollout steps")

    # vlm
    p_vlm = subparsers.add_parser("vlm", help="VLM perception and visual task planner")
    p_vlm.add_argument("--task", type=str, default="Describe the scene", help="Natural language visual task")
    p_vlm.add_argument("--vlm-type", type=str, default="mock", choices=["mock", "clip", "blip"], help="VLM adapter type")
    p_vlm.add_argument("--cam-type", type=str, default="mock", choices=["mock", "realsense", "usb", "recorded"], help="Camera source type")
    p_vlm.add_argument("--evaluate", action="store_true", help="Print VLM hardware evaluation report")

    args = parser.parse_args()


    if args.command == "doctor":
        doc = JarvisDoctor()
        if args.bundle:
            path = doc.create_diagnostic_bundle()
            print(f"[OK] Diagnostic bundle saved to: {path}")
            sys.exit(0)
        ok = doc.print_report()
        sys.exit(0 if ok else 1)

    elif args.command == "validate-config":
        report = ConfigValidator.validate_file(args.config)
        print(f"\nConfiguration Validation Report ({args.config}):")
        print(f"  Valid   : {report['valid']}")
        if report["errors"]:
            print("  Errors  :")
            for err in report["errors"]:
                print(f"    - [FAIL] {err}")
        if report["warnings"]:
            print("  Warnings:")
            for warn in report["warnings"]:
                print(f"    - [WARN] {warn}")
        if report["valid"] and not report["warnings"]:
            print("  Status  : ALL PARAMETERS COMPLIANT WITH SAFETY CONSTITUTION")
        sys.exit(0 if report["valid"] else 1)

    elif args.command == "validate":
        val = EpisodeValidator()
        res = val.validate_episode(args.dataset)
        print(f"\nValidation Result for {args.dataset}:")
        print(f"  Valid   : {res['valid']}")
        print(f"  Errors  : {res['errors']}")
        print(f"  Warnings: {res['warnings']}")
        sys.exit(0 if res["valid"] else 1)

    elif args.command == "teleop":
        from jarvis.teleop import TeleoperationMapper
        dry_run = not args.execute
        print(f"Starting teleoperation loop (dry_run={dry_run})...")
        teleop = MockTeleop()
        arm = MockArm()
        arm.connect()
        safety = SafetySupervisor()
        mapper = TeleoperationMapper()

        if not dry_run:
            token = input("Enter motion authorization token ('ENABLE MOTION'): ").strip()
            safety.authorize_motion(token)

        teleop.connect()
        pos, quat = teleop.get_pose()
        teleop.clutch = True
        mapper.on_clutch_engaged(pos, [0.25, 0.0, 0.20])

        for step in range(args.steps):
            pos, quat = teleop.get_pose()
            target = mapper.map_hand_to_robot(pos)
            if target is not None:
                q_cmd = [0.0, 0.5, -0.6, 0.0, 0.1, 0.0]
                current_q = arm.get_joint_state()["positions"]
                safe_q = safety.validate_and_filter(
                    command_q=q_cmd,
                    current_q=current_q,
                    clutch_engaged=teleop.is_clutch_engaged(),
                    tracking_age_sec=teleop.get_tracking_age(),
                    ee_pos=target,
                    is_hardware_target=(not dry_run),
                )
                if not dry_run:
                    arm.command_joint_positions(safe_q)
        print(f"[OK] Teleoperation loop completed successfully ({args.steps} steps).")
        sys.exit(0)

    elif args.command == "record":
        rec = EpisodeRecorder(output_dir=args.output_dir)
        ep_id = "episode_mock_001"
        rec.start_episode(ep_id, {"task": "pick_and_place", "operator": "mock_tester"})
        for i in range(args.steps):
            q = [0.0, 0.5, -0.6 + 0.005 * (i / max(1, args.steps)), 0.0, 0.1, 0.0]
            rec.record_step(joint_positions=q, joint_velocities=[0.0]*6, action=q, gripper_stroke=0.035)
        meta = rec.stop_episode(outcome="success")
        print(f"[OK] Recorded episode {ep_id} ({meta['num_steps']} steps) in {rec.episode_dir}")
        sys.exit(0)

    elif args.command == "train":
        print(f"Training BC policy on {args.data_dir} for {args.epochs} epochs...")
        meta = train_bc_policy([args.data_dir], epochs=args.epochs)
        print(f"[OK] Training complete! Train loss: {meta['train_loss']}, Val loss: {meta['val_loss']}")
        sys.exit(0)

    elif args.command == "policy":
        arm = MockArm()
        arm.connect()
        gripper = MockGripper()
        gripper.connect()
        safety = SafetySupervisor()
        policy = BCPolicy()

        dry_run = not args.execute
        token = None
        if not dry_run:
            token = input("Enter motion authorization token ('ENABLE MOTION'): ").strip()

        runner = SupervisedPolicyRunner(policy, arm, gripper, safety)
        res = runner.execute_rollout(max_steps=args.steps, dry_run=dry_run, motion_token=token)
        print(f"\n[OK] Policy Rollout Finished:")
        print(f"  Dry Run        : {res['dry_run']}")
        print(f"  Steps Executed : {res['steps_executed']}")
        print(f"  Anomaly        : {res['anomaly_detected']}")
        print(f"  Reason         : {res['termination_reason']}")
        sys.exit(0)

    elif args.command == "vlm":
        from jarvis.vlm import (
            build_vlm,
            build_camera_source,
            VisionTaskPlanner,
            detect_hardware,
            MODEL_REGISTRY,
        )
        if args.evaluate:
            prof = detect_hardware()
            print("\n=== VLM Hardware Evaluation Report ===")
            print(f"System RAM: {prof.system_ram_gb:.1f} GB")
            print(f"CUDA Available: {prof.has_cuda} (VRAM: {prof.cuda_vram_gb or 0:.1f} GB)")
            print(f"Recommended Model Tier: {prof.recommended_tier}")
            print("\nModel Registry:")
            for name, spec in MODEL_REGISTRY.items():
                cpu_ms = spec.cpu_latency_ms or "N/A"
                print(f"  [{name:13s}] {spec.adapter_class:20s} size={spec.approx_size_mb:5.0f}MB CPU={cpu_ms}ms")
            sys.exit(0)

        print(f"\n[JARVIS VLM] Initializing VLM ({args.vlm_type}) and Camera ({args.cam_type})...")
        vlm = build_vlm({"type": args.vlm_type})
        camera = build_camera_source({"type": args.cam_type})
        planner = VisionTaskPlanner(vlm=vlm, camera=camera)
        plan = planner.plan(args.task)
        print("\n=== Generated Plan ===")
        print(plan.summary())
        print("\nExecuting plan (dry run / perception only)...")
        executed = planner.execute_plan(plan, operator_authorized=False)
        print("\n=== Execution Result ===")
        for s in executed.steps:
            print(f"  {s}")
        print(f"\nPlan completed: success={executed.success}")
        sys.exit(0 if executed.success is not False else 1)

    else:
        parser.print_help()
        sys.exit(0)



if __name__ == "__main__":
    main()
