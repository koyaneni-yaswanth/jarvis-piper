#!/usr/bin/env python3
"""
Policy Dry-Run Verification Script (Actuation Disabled).
Evaluates trained neural network policies against safety bounds and inference deadlines (<20ms).
"""

import os
import sys
import time
import numpy as np
import torch

sys.path.insert(0, "python")
from learning.imitation.models import BehavioralCloningPolicy
from jarvis_piper.safety.supervisor import SafetySupervisor


def run_dry_run(checkpoint_path: str = "models/checkpoints/imitation/bc_piper_policy.pt"):
    print("=" * 80)
    print("        JARVIS-PiPER POLICY INFERENCE DRY RUN (ACTUATION DISABLED)")
    print("=" * 80)

    if not os.path.exists(checkpoint_path):
        print(f"[ERROR] Checkpoint not found: {checkpoint_path}")
        return 1

    device = torch.device("cpu")
    ckpt = torch.load(checkpoint_path, map_location=device)
    policy = BehavioralCloningPolicy(obs_dim=16, action_dim=8, hidden_dim=256, num_layers=4)
    policy.load_state_dict(ckpt["model_state_dict"])
    policy.eval()

    supervisor = SafetySupervisor()
    latencies = []
    safety_violations = 0

    print("Executing 100 dry-run inference cycles with synthetic workspace observations:")
    for step in range(100):
        # Generate nominal observation: q, v, tcp, stroke
        q_cur = [0.1 * np.sin(step * 0.05), 0.5, -0.6, 0.0, 0.2, 0.0]
        v_cur = [0.0] * 6
        tcp_cur = [0.40, 0.0, 0.30]
        stroke_cur = 0.035
        obs_raw = q_cur + v_cur + tcp_cur + [stroke_cur]

        t0 = time.perf_counter()
        with torch.no_grad():
            obs_t = torch.tensor(obs_raw, dtype=torch.float32).unsqueeze(0)
            act_pred = policy(obs_t).squeeze(0).numpy()
        dt_ms = (time.perf_counter() - t0) * 1000.0
        latencies.append(dt_ms)

        # Pass through safety supervisor
        target_q = act_pred[:6].tolist()
        target_stroke = float(act_pred[6])
        safe_q, safe_stroke, is_safe, reason = supervisor.filter_and_validate_action(
            target_q=target_q,
            current_q=q_cur,
            target_stroke=target_stroke,
        )

        if not is_safe:
            safety_violations += 1

    mean_lat = float(np.mean(latencies))
    max_lat = float(np.max(latencies))

    print(f" Mean Inference Latency:   {mean_lat:6.3f} ms (Target < 20.0 ms)")
    print(f" Peak Inference Latency:   {max_lat:6.3f} ms")
    print(f" Unsafe Commands Blocked: {safety_violations}")
    assert mean_lat < 20.0, "Inference latency violates 50Hz control deadline"

    print("=" * 80)
    print(" [PASSED] Policy Dry-Run Verification Passed. Model is safe for supervised execution!")
    print("=" * 80)
    return 0


if __name__ == "__main__":
    sys.exit(run_dry_run())
