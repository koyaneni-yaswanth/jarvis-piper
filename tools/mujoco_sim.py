#!/usr/bin/env python3
"""
JARVIS-PiPER: MuJoCo Simulation Runner & CLI.
Runs interactive or headless PiPER arm simulations in MuJoCo:
- Joint space & Cartesian reaching tasks
- Offscreen synthetic camera recording (RGB + Depth)
- Evaluation of trained BC and ACT policies in simulation
- Exports simulated episodes labeled with DATA_ORIGIN = SIMULATION_MUJOCO

Usage:
    python tools/mujoco_sim.py --steps 50 --record
    python tools/mujoco_sim.py --steps 50 --policy act --gui
"""

import os
import sys
import time
import json
import argparse
from pathlib import Path
import numpy as np

# Ensure repo root is on sys.path
_repo_dir = str(Path(__file__).resolve().parent.parent)
if _repo_dir not in sys.path:
    sys.path.insert(0, _repo_dir)

from simulation.mujoco_env import MuJoCoPiPEREnv


def main():
    parser = argparse.ArgumentParser(description="JARVIS-PiPER MuJoCo Simulation Runner")
    parser.add_argument("--steps", type=int, default=50, help="Number of simulation steps to run")
    parser.add_argument("--gui", action="store_true", help="Launch interactive passive MuJoCo viewer")
    parser.add_argument("--record", action="store_true", help="Record simulation episode to disk")
    parser.add_argument("--out-dir", type=str, default="data/simulation", help="Output directory for recorded episodes")
    parser.add_argument("--task", type=str, default="reach_cube", help="Simulation task name")
    parser.add_argument("--policy", choices=["nominal", "bc", "act"], default="nominal", help="Policy to drive simulation")
    args = parser.parse_args()

    print("=" * 80)
    print("      JARVIS-PiPER :: MUJOCO PHYSICS SIMULATION")
    print("=" * 80)
    print(f" Task Name   : {args.task}")
    print(f" Policy Mode : {args.policy.upper()}")
    print(f" Total Steps : {args.steps}")
    print(f" GUI Viewer  : {'REQUESTED' if args.gui else 'HEADLESS'}")
    print(f" Data Origin : SIMULATION_MUJOCO (Strictly isolated from physical datasets)")
    print("=" * 80)

    env = MuJoCoPiPEREnv()
    obs = env.reset(seed=42)

    viewer = None
    if args.gui:
        viewer = env.launch_passive_viewer()

    policy_model = None
    if args.policy in ("bc", "act"):
        ckpt_path = f"models/checkpoints/imitation/{args.policy}_piper_policy.pt"
        if os.path.exists(ckpt_path):
            import torch
            from learning.imitation.models import BehavioralCloningPolicy, ActionChunkingPolicy
            ckpt = torch.load(ckpt_path, map_location="cpu")
            obs_d = ckpt.get("obs_dim", 8)
            act_d = ckpt.get("action_dim", 8)
            if args.policy == "act":
                policy_model = ActionChunkingPolicy(obs_dim=obs_d, action_dim=act_d, chunk_size=5)
            else:
                policy_model = BehavioralCloningPolicy(obs_dim=obs_d, action_dim=act_d)
            policy_model.load_state_dict(ckpt["model_state_dict"])
            if "obs_mean" in ckpt and "obs_std" in ckpt:
                policy_model.set_normalization_stats(ckpt["obs_mean"], ckpt["obs_std"])
            policy_model.eval()
            print(f"[INFO] Loaded trained {args.policy.upper()} checkpoint from {ckpt_path}")
        else:
            print(f"[WARN] Checkpoint {ckpt_path} not found. Falling back to nominal trajectory.")

    # Target pose near the red cube
    cube_pos = obs["cube_position"]
    q_reach, reach_ok = env.kinematics.compute_ik(
        target_pos=[cube_pos[0], cube_pos[1], cube_pos[2] + 0.05],
        q_init=obs["joint_positions"],
    )
    if not reach_ok or q_reach is None:
        q_reach = [0.15, 0.45, -0.60, 0.0, 0.15, 0.0]

    records = []
    t0 = time.time()

    print(f"\n[INFO] Stepping MuJoCo simulation for {args.steps} steps...")
    for step in range(args.steps):
        current_q = obs["joint_positions"]
        stroke = obs["gripper_stroke"]

        if policy_model is not None:
            # 8D observation vector [x, y, z, qx, qy, qz, qw, stroke_mm]
            tcp = obs["tcp_pose"]["position"]
            quat = obs["tcp_pose"]["quaternion"]
            obs_vec = tcp + quat + [stroke * 1000.0]
            with torch.no_grad():
                pred = policy_model.predict(obs_vec)
            # Map predicted delta to joint target
            pred_pos = pred[:3]
            ik_cmd, ik_ok = env.kinematics.compute_ik(pred_pos, q_init=current_q)
            target_q = ik_cmd if (ik_ok and ik_cmd is not None) else q_reach
            target_stroke = float(np.clip(pred[7] / 1000.0, 0.0, 0.070)) if len(pred) > 7 else 0.035
        else:
            # Smooth interpolation toward reach target
            alpha = min(1.0, (step + 1) / max(1, args.steps * 0.75))
            target_q = (np.array(env.q_home) * (1.0 - alpha) + np.array(q_reach) * alpha).tolist()
            target_stroke = 0.035 if step < (args.steps * 0.8) else 0.010

        obs, reward, done, info = env.step(target_q, target_stroke)
        env.sync_viewer()

        if args.record:
            rec = {
                "step": step,
                "sim_time": obs["sim_time"],
                "joint_positions": obs["joint_positions"],
                "joint_velocities": obs["joint_velocities"],
                "tcp_pose": obs["tcp_pose"],
                "gripper_stroke": obs["gripper_stroke"],
                "action": target_q + [target_stroke],
                "cube_position": obs["cube_position"],
                "dist_to_cube_m": info["dist_to_cube_m"],
                "data_origin": "SIMULATION_MUJOCO",
            }
            records.append(rec)

        if (step + 1) % 10 == 0 or step == args.steps - 1:
            print(f" Step [{step+1:3d}/{args.steps:3d}] | Sim Time: {obs['sim_time']:.3f}s | Dist to Cube: {info['dist_to_cube_m']:.4f}m")

    elapsed = time.time() - t0
    fps = args.steps / max(0.001, elapsed)
    print(f"\n[PASS] Simulation finished in {elapsed:.3f}s ({fps:.1f} steps/s).")

    # Render a verification frame from wrist camera
    wrist_rgb = env.render_camera("wrist_camera")
    wrist_depth = env.render_camera("wrist_camera", depth=True)
    print(f" Camera Render Check: Wrist RGB shape={wrist_rgb.shape}, Depth min/max={wrist_depth.min():.3f}m / {wrist_depth.max():.3f}m")

    if args.record and records:
        timestamp_str = time.strftime("%Y%m%d_%H%M%S")
        ep_dir = Path(args.out_dir) / f"sim_ep_{args.task}_{timestamp_str}"
        ep_dir.mkdir(parents=True, exist_ok=True)

        telem_p = ep_dir / "sim_telemetry.jsonl"
        with open(telem_p, "w", encoding="utf-8") as f:
            for r in records:
                f.write(json.dumps(r) + "\n")

        meta = {
            "episode_id": ep_dir.name,
            "data_origin": "SIMULATION_MUJOCO",
            "task": args.task,
            "policy": args.policy,
            "total_steps": len(records),
            "sim_duration_s": obs["sim_time"],
            "wall_duration_s": round(elapsed, 3),
            "final_dist_to_cube_m": info["dist_to_cube_m"],
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        with open(ep_dir / "metadata.json", "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2)

        print(f"[SUCCESS] Recorded simulation episode saved: {ep_dir.resolve()}")

    env.close()


if __name__ == "__main__":
    main()
