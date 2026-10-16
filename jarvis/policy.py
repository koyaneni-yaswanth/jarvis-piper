"""
JARVIS-PiPER: Supervised Policy Execution.
Runs trained BC policies under strict supervision:
- Defaults to --dry-run (actuation disabled).
- Real hardware actuation requires --execute AND operator token "ENABLE MOTION".
- Every policy action passes through the SafetySupervisor before transmission.
- Automatically halts on anomalies (excessive action clamping, tracking loss, watchdog timeout).
- Logs every rollout to disk.
"""

import os
import json
import time
from typing import Dict, Any, List, Optional
import numpy as np

from jarvis.safety import SafetySupervisor
from jarvis.hardware import ArmInterface, GripperInterface
from jarvis.train import BCPolicy


try:
    from world_model.spatial import PiperKinematics
except ImportError:
    from python.world_model.spatial import PiperKinematics


class SupervisedPolicyRunner:
    """
    Supervised rollout orchestrator for physical and simulated deployment.
    """

    def __init__(
        self,
        policy: Any,
        arm: ArmInterface,
        gripper: GripperInterface,
        safety_supervisor: SafetySupervisor,
        log_dir: str = "logs/rollouts",
    ):
        self.policy = policy
        self.arm = arm
        self.gripper = gripper
        self.safety = safety_supervisor
        self.kinematics = PiperKinematics()
        self.log_dir = log_dir
        os.makedirs(log_dir, exist_ok=True)

    def execute_rollout(
        self,
        max_steps: int = 100,
        control_hz: float = 20.0,
        dry_run: bool = True,
        motion_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Executes a supervised policy rollout.
        dry_run: If True, computes actions and safety checks but skips arm transmission.
        """
        if not dry_run:
            if motion_token != "ENABLE MOTION":
                raise PermissionError("Physical execution rejected: Session token 'ENABLE MOTION' required!")
            self.safety.authorize_motion(motion_token)

        rollout_id = f"rollout_{int(time.time())}"
        records: List[Dict[str, Any]] = []
        clamped_count = 0
        anomaly_detected = False
        reason = "completed_nominal"

        dt = 1.0 / control_hz
        start_time = time.time()

        # Arm initial pose
        initial_q = self.arm.get_joint_state()["positions"]
        arm_start_pos, _ = self.kinematics.compute_fk(initial_q)

        # Baseline tracker pose for relative incremental policy execution
        # (Default canonical demonstration starting pose in tracking frame)
        canonical_tracker_start = [0.067, 0.717, -0.167, -0.266, 0.333, 0.577, 0.695, 99.0]
        tracker_curr = list(canonical_tracker_start)

        for step in range(max_steps):
            step_start = time.time()

            # 1. Acquire current robot observation
            state = self.arm.get_joint_state()
            current_q = state["positions"]
            stroke = self.gripper.get_stroke()
            target_dim = getattr(self.policy, "obs_dim", 7)

            if target_dim == 8:
                # 8D Cartesian demonstration policy [x, y, z, qx, qy, qz, qw, grip_mm]
                pred_act = self.policy.predict(tracker_curr)
                tracker_curr = list(pred_act)

                # Compute Cartesian delta relative to demonstration origin
                delta_pos = np.array(pred_act[:3]) - np.array(canonical_tracker_start[:3])
                # Scale delta into arm workspace (0.5 scale factor for gentle motion)
                target_pos = np.array(arm_start_pos) + delta_pos * 0.5
                target_stroke_mm = pred_act[7] if len(pred_act) > 7 else stroke * 1000.0
                target_stroke = float(np.clip(target_stroke_mm / 1000.0, 0.0, 0.070))

                # Numerical IK
                ik_q, ik_ok = self.kinematics.compute_ik(list(target_pos), q_init=current_q)
                if ik_ok and ik_q is not None:
                    target_q = ik_q
                else:
                    target_q = list(current_q)

                obs = list(tracker_curr)
            else:
                # 7D Joint-space policy [q1, q2, q3, q4, q5, q6, stroke]
                obs = current_q + [stroke]
                pred_act = self.policy.predict(obs)
                target_q = pred_act[:6]
                target_stroke = pred_act[6] if len(pred_act) > 6 else stroke

            # Clamp policy unconstrained output to physical joint limits
            clamped_target_q = []
            for j in range(6):
                lim_min, lim_max = self.safety.JOINT_LIMITS[j]
                clamped_target_q.append(float(np.clip(target_q[j], lim_min, lim_max)))

            # Check clamping delta for anomaly tracking
            if np.max(np.abs(np.array(clamped_target_q) - np.array(target_q))) > 0.05:
                clamped_count += 1

            # 3. Pass through Safety Supervisor
            try:
                safe_q = self.safety.validate_and_filter(
                    command_q=clamped_target_q,
                    current_q=current_q,
                    clutch_engaged=True,
                    is_hardware_target=(not dry_run),
                )
            except Exception as e:
                anomaly_detected = True
                reason = f"Safety stop triggered: {e}"
                break

            # 4. Actuate only if NOT dry-run
            if not dry_run:
                self.arm.command_joint_positions(safe_q)
                self.gripper.command_stroke(target_stroke)
            else:
                if hasattr(self.arm, "q"):
                    self.arm.q = list(safe_q)
                if hasattr(self.gripper, "stroke"):
                    self.gripper.stroke = float(target_stroke)

            records.append({
                "step": step,
                "timestamp": time.time() - start_time,
                "obs": obs,
                "pred_action": pred_act,
                "safe_action": safe_q,
                "dry_run": dry_run,
            })

            # Check anomaly rate (if policy consistently attempts unsafe jumps)
            if clamped_count > 15:
                anomaly_detected = True
                reason = "Anomaly hold: Policy requested > 15 out-of-limit action jumps."
                break

            # Rate maintain
            elapsed = time.time() - step_start
            if elapsed < dt:
                time.sleep(dt - elapsed)

        # Log rollout
        log_file = os.path.join(self.log_dir, f"{rollout_id}.jsonl")
        with open(log_file, "w", encoding="utf-8") as f:
            for r in records:
                f.write(json.dumps(r) + "\n")

        return {
            "rollout_id": rollout_id,
            "dry_run": dry_run,
            "steps_executed": len(records),
            "clamped_steps": clamped_count,
            "anomaly_detected": anomaly_detected,
            "termination_reason": reason,
            "log_file": log_file,
        }
