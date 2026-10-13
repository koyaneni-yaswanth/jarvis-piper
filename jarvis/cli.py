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
from jarvis.doctor import JarvisDoctor
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

    # validate
    p_val = subparsers.add_parser("validate", help="Validate recorded episode dataset")
    p_val.add_argument("--dataset", type=str, default="data/raw/episode_mock_001", help="Path to episode or dataset")

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

    args = parser.parse_args()

    if args.command == "doctor":
        doc = JarvisDoctor()
        if args.bundle:
            path = doc.create_diagnostic_bundle()
            print(f"[OK] Diagnostic bundle saved to: {path}")
            sys.exit(0)
        ok = doc.print_report()
        sys.exit(0 if ok else 1)

    elif args.command == "validate":
        val = EpisodeValidator()
        res = val.validate_episode(args.dataset)
        print(f"\nValidation Result for {args.dataset}:")
        print(f"  Valid   : {res['valid']}")
        print(f"  Errors  : {res['errors']}")
        print(f"  Warnings: {res['warnings']}")
        sys.exit(0 if res["valid"] else 1)

    elif args.command == "record":
        rec = EpisodeRecorder(output_dir=args.output_dir)
        ep_id = "episode_mock_001"
        rec.start_episode(ep_id, {"task": "pick_and_place", "operator": "mock_tester"})
        for i in range(args.steps):
            q = [0.1 * i / args.steps] * 6
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
        token = "ENABLE MOTION" if args.execute else None

        runner = SupervisedPolicyRunner(policy, arm, gripper, safety)
        res = runner.execute_rollout(max_steps=args.steps, dry_run=dry_run, motion_token=token)
        print(f"\n[OK] Policy Rollout Finished:")
        print(f"  Dry Run        : {res['dry_run']}")
        print(f"  Steps Executed : {res['steps_executed']}")
        print(f"  Anomaly        : {res['anomaly_detected']}")
        print(f"  Reason         : {res['termination_reason']}")
        sys.exit(0)

    else:
        parser.print_help()
        sys.exit(0)


if __name__ == "__main__":
    main()
