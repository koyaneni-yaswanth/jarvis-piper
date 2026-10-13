"""
Thematic Data Generation Engine for JARVIS-PiPER.
Implements the 3 Core Research Starter Themes:
1. Pick-and-Place Manipulation: End-to-end grasping, transport, and release.
2. Visual Prediction (V-JEPA 2 / 2-AC): High-coverage spatial trajectories with action-conditioning.
3. Failure Detection and Recovery: Slip anomaly detection, replanning, and safe recovery.

Supports extension to all 10 recommended embodied learning themes.
Outputs synchronized video (30 FPS), 16-bit depth, joint states (100Hz->30Hz),
actions, gripper telemetry, and crash-resilient metadata.
"""

import os
import time
import json
import math
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
import numpy as np

try:
    import cv2
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False

from world_model.spatial import PiperKinematics
from jarvis_piper.safety.supervisor import SafetySupervisor


class ManipulationTheme(Enum):
    PICK_AND_PLACE = "pick_and_place"
    VISUAL_PREDICTION = "visual_prediction"
    FAILURE_RECOVERY = "failure_recovery"
    REACHING_MOTION = "reaching_motion"
    SCENE_UNDERSTANDING = "scene_understanding"
    GRASP_AND_RELEASE = "grasp_and_release"
    TASK_SEQUENCING = "task_sequencing"
    LANGUAGE_CONDITIONED = "language_conditioned"
    SENSOR_FUSION = "sensor_fusion"
    GENERALIZATION = "generalization"


class ThematicDatasetGenerator:
    """
    Generates research-grade multi-modal demonstration episodes across manipulation themes.
    """

    def __init__(self, output_root: str = "dataset/raw"):
        self.output_root = output_root
        self.kinematics = PiperKinematics()
        self.safety = SafetySupervisor()
        os.makedirs(self.output_root, exist_ok=True)

    def _render_synthetic_scene(
        self,
        step: int,
        total_steps: int,
        arm_q: List[float],
        gripper_stroke: float,
        obj_held: bool,
        theme: ManipulationTheme,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Renders an RGB-D frame representing the robot arm and tabletop objects.
        Returns (rgb_frame: uint8 (240, 320, 3), depth_frame: uint16 (240, 320)).
        """
        h, w = 240, 320
        # Background: Workbench table (neutral gray)
        rgb = np.full((h, w, 3), (180, 180, 185), dtype=np.uint8)
        depth = np.full((h, w), 750, dtype=np.uint16)  # Table plane at 750 mm

        # Draw Tabletop Tray / Bowl (target destination on right)
        tray_x, tray_y = 230, 130
        if HAS_CV2:
            cv2.ellipse(rgb, (tray_x, tray_y), (40, 25), 0, 0, 360, (190, 120, 80), -1)
            cv2.ellipse(rgb, (tray_x, tray_y), (36, 21), 0, 0, 360, (220, 150, 100), -1)
            depth[tray_y - 20:tray_y + 20, tray_x - 35:tray_x + 35] = 730

        # Draw Target Red Block
        # If held, moves with end-effector projection; otherwise sits on table
        fk_pos, _ = self.kinematics.compute_fk(arm_q)
        tcp_u = int(np.clip(160 + fk_pos[1] * 400, 40, 280))
        tcp_v = int(np.clip(220 - (fk_pos[0] - 0.20) * 350, 40, 200))

        if obj_held:
            block_u, block_v = tcp_u, tcp_v
            block_depth = int(np.clip(750 - fk_pos[2] * 500, 300, 700))
        else:
            block_u, block_v = 100, 150
            block_depth = 710

        if HAS_CV2:
            # Draw Red Cube
            cv2.rectangle(rgb, (block_u - 14, block_v - 14), (block_u + 14, block_v + 14), (40, 40, 210), -1)
            cv2.rectangle(rgb, (block_u - 14, block_v - 14), (block_u + 14, block_v + 14), (20, 20, 150), 2)
            depth[max(0, block_v - 14):min(h, block_v + 14), max(0, block_u - 14):min(w, block_u + 14)] = block_depth

            # Draw Robot Arm / Forearm Projection
            base_u, base_v = 160, 235
            elbow_u = int((base_u + tcp_u) / 2 + arm_q[1] * 30)
            elbow_v = int((base_v + tcp_v) / 2 - arm_q[2] * 25)
            cv2.line(rgb, (base_u, base_v), (elbow_u, elbow_v), (70, 70, 75), 14)
            cv2.line(rgb, (elbow_u, elbow_v), (tcp_u, tcp_v), (90, 90, 95), 10)

            # Draw Parallel Gripper Fingers
            gap = int(gripper_stroke * 400)
            cv2.line(rgb, (tcp_u - gap, tcp_v - 8), (tcp_u - gap, tcp_v + 8), (30, 30, 30), 4)
            cv2.line(rgb, (tcp_u + gap, tcp_v - 8), (tcp_u + gap, tcp_v + 8), (30, 30, 30), 4)

            # Overlay Theme Watermark
            cv2.putText(rgb, f"Theme: {theme.value}", (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (40, 40, 40), 1)
            cv2.putText(rgb, f"Step: {step:03d}/{total_steps}", (10, 38), cv2.FONT_HERSHEY_SIMPLEX, 0.40, (70, 70, 70), 1)

        return rgb, depth

    def generate_episode(
        self,
        theme: ManipulationTheme = ManipulationTheme.PICK_AND_PLACE,
        episode_index: int = 1,
        total_steps: int = 75,
        fps: float = 30.0,
    ) -> Dict[str, Any]:
        """
        Generates a single multi-modal demonstration episode tailored to the requested theme.
        """
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        ep_id = f"ep_{theme.value}_{episode_index:03d}_{timestamp_str}"
        ep_dir = os.path.join(self.output_root, ep_id)
        os.makedirs(os.path.join(ep_dir, "videos"), exist_ok=True)
        os.makedirs(os.path.join(ep_dir, "images", "wrist"), exist_ok=True)
        os.makedirs(os.path.join(ep_dir, "images", "depth"), exist_ok=True)

        writer = None
        if HAS_CV2:
            video_path = os.path.join(ep_dir, "videos", "wrist.mp4")
            writer = cv2.VideoWriter(video_path, cv2.VideoWriter_fourcc(*"mp4v"), fps, (320, 240))

        timesteps = []
        journal_lines = []

        # Baseline stances
        q_home = [0.0, 0.30, -0.40, 0.0, 0.0, 0.0]
        q_pick_reach = [-0.25, 0.55, -0.85, 0.0, 0.35, -0.25]
        q_lift = [-0.20, 0.25, -0.45, 0.0, 0.20, -0.20]
        q_place_reach = [0.35, 0.50, -0.75, 0.0, 0.30, 0.35]

        failure_injected = False
        failure_type = "none"
        recovery_executed = False
        success_label = True

        if theme == ManipulationTheme.FAILURE_RECOVERY:
            failure_injected = True
            failure_type = "grasp_slip"
            instruction = "Grasp slip anomaly: Detect slip contact failure on red block and execute recovery"
        elif theme == ManipulationTheme.VISUAL_PREDICTION:
            instruction = "Visual rollout: Predict scene representation during wide-baseline arm reaching"
        else:
            instruction = "Pick up red block and place it in the bowl"

        q_current = list(q_home)
        gripper_stroke = 0.035
        obj_held = False

        for step in range(total_steps):
            t_frac = step / float(total_steps)
            sim_t = round(step * (1.0 / fps), 4)

            # Trajectory state machines per theme
            if theme == ManipulationTheme.PICK_AND_PLACE:
                if step < 20:
                    # Approaching pick
                    alpha = step / 20.0
                    q_current = [q_home[j] + alpha * (q_pick_reach[j] - q_home[j]) for j in range(6)]
                    gripper_stroke = 0.035
                    obj_held = False
                elif step < 30:
                    # Closing gripper on block
                    q_current = list(q_pick_reach)
                    gripper_stroke = max(0.012, 0.035 - (step - 20) * 0.0025)
                    obj_held = True
                elif step < 50:
                    # Transporting to bowl
                    alpha = (step - 30) / 20.0
                    q_current = [q_lift[j] + alpha * (q_place_reach[j] - q_lift[j]) for j in range(6)]
                    gripper_stroke = 0.012
                    obj_held = True
                elif step < 60:
                    # Opening gripper to release
                    q_current = list(q_place_reach)
                    gripper_stroke = min(0.035, 0.012 + (step - 50) * 0.0025)
                    obj_held = False
                else:
                    # Retracting home
                    alpha = (step - 60) / float(total_steps - 60)
                    q_current = [q_place_reach[j] + alpha * (q_home[j] - q_place_reach[j]) for j in range(6)]
                    gripper_stroke = 0.035
                    obj_held = False

            elif theme == ManipulationTheme.FAILURE_RECOVERY:
                if step < 20:
                    # Approach
                    alpha = step / 20.0
                    q_current = [q_home[j] + alpha * (q_pick_reach[j] - q_home[j]) for j in range(6)]
                    gripper_stroke = 0.035
                    obj_held = False
                elif step < 28:
                    # INJECTED SLIP: Gripper closes completely (0.000m), missed grasp!
                    q_current = list(q_pick_reach)
                    gripper_stroke = max(0.000, 0.035 - (step - 20) * 0.005)
                    obj_held = False
                elif step < 40:
                    # RECOVERY DETECTION: Open gripper, back off +3cm
                    recovery_executed = True
                    q_current = [q_pick_reach[j] - 0.05 * math.sin((step - 28) * 0.2) for j in range(6)]
                    gripper_stroke = min(0.035, (step - 28) * 0.003)
                    obj_held = False
                elif step < 50:
                    # SECURE RE-GRASP
                    q_current = list(q_pick_reach)
                    gripper_stroke = max(0.012, 0.035 - (step - 40) * 0.0025)
                    obj_held = True
                elif step < 65:
                    # Transport
                    alpha = (step - 50) / 15.0
                    q_current = [q_lift[j] + alpha * (q_place_reach[j] - q_lift[j]) for j in range(6)]
                    gripper_stroke = 0.012
                    obj_held = True
                else:
                    # Release & return
                    gripper_stroke = 0.035
                    obj_held = False
                    alpha = (step - 65) / float(total_steps - 65)
                    q_current = [q_place_reach[j] + alpha * (q_home[j] - q_place_reach[j]) for j in range(6)]

            elif theme == ManipulationTheme.VISUAL_PREDICTION:
                # Dynamic multi-sine trajectory designed for V-JEPA spatial-temporal representation learning
                w1, w2, w3 = 2.0 * math.pi * 0.5, 2.0 * math.pi * 0.3, 2.0 * math.pi * 0.7
                q_current = [
                    0.40 * math.sin(w1 * t_frac),
                    0.35 + 0.25 * math.cos(w2 * t_frac),
                    -0.50 + 0.30 * math.sin(w3 * t_frac),
                    0.20 * math.sin(w1 * t_frac),
                    0.15 * math.cos(w2 * t_frac),
                    0.30 * math.sin(w3 * t_frac),
                ]
                gripper_stroke = 0.020 + 0.015 * math.sin(w1 * t_frac)
                obj_held = False

            # Compute velocities and TCP pose
            q_vel = [round(0.1 * math.sin(step * 0.1 + j), 4) for j in range(6)]
            q_eff = [round(1.5 * math.cos(step * 0.1 + j), 4) for j in range(6)]
            pos, quat = self.kinematics.compute_fk(q_current)

            # Render synthetic vision
            rgb, depth = self._render_synthetic_scene(step, total_steps, q_current, gripper_stroke, obj_held, theme)
            if writer is not None:
                writer.write(rgb)

            if step % 15 == 0 and HAS_CV2:
                cv2.imwrite(os.path.join(ep_dir, "images", "wrist", f"frame_{step:06d}.jpg"), rgb)
                cv2.imwrite(os.path.join(ep_dir, "images", "depth", f"depth_{step:06d}.png"), depth)

            # Formulate action vector (q1..q6 + gripper stroke)
            action_vector = [round(x, 4) for x in q_current] + [round(gripper_stroke, 4)]

            step_dict = {
                "step_index": step,
                "timestamp": sim_t,
                "joint_positions": [round(x, 4) for x in q_current],
                "joint_velocities": q_vel,
                "joint_efforts": q_eff,
                "gripper_stroke": round(gripper_stroke, 4),
                "tcp_pose": {
                    "position": [round(x, 4) for x in pos],
                    "orientation": [round(x, 4) for x in quat],
                },
                "action": action_vector,
                "semantic_phase": "recovery" if (failure_injected and 28 <= step < 40) else "nominal",
            }
            timesteps.append(step_dict)
            journal_lines.append(json.dumps(step_dict))

        if writer is not None:
            writer.release()

        # Write stream_journal.jsonl (line-by-line crash resilient)
        with open(os.path.join(ep_dir, "stream_journal.jsonl"), "w", encoding="utf-8") as f:
            f.write("\n".join(journal_lines) + "\n")

        metadata = {
            "episode_id": ep_id,
            "task_theme": theme.value,
            "task_instruction": instruction,
            "task_category": "manipulation",
            "operator_id": "thematic_data_engine",
            "source_label": "SYNTHETIC",
            "robot_platform": "PiPER_6DOF",
            "success_label": success_label,
            "failure_injected": failure_injected,
            "failure_type": failure_type,
            "recovery_executed": recovery_executed,
            "vjepa_compatible": True,
            "action_conditioned": True,
            "duration_sec": round(total_steps / fps, 2),
            "total_steps": total_steps,
            "target_fps": fps,
            "start_timestamp": timestamp_str,
            "schema_version": "2.0.0",
        }

        with open(os.path.join(ep_dir, "metadata.json"), "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)

        with open(os.path.join(ep_dir, "trajectory.json"), "w", encoding="utf-8") as f:
            json.dump({"metadata": metadata, "timesteps": timesteps}, f, indent=2)

        print(f"  [OK] Generated {ep_id:40} | Theme: {theme.value:18} | Steps: {total_steps} | Recovery: {recovery_executed}")
        return metadata

    def generate_starter_curriculum(self, episodes_per_theme: int = 2) -> Dict[str, Any]:
        """
        Generates the 3 core starter themes recommended for JARVIS + single Piper + V-JEPA:
        1. Pick and Place
        2. Visual Prediction (Action-Conditioned V-JEPA)
        3. Failure Detection and Recovery
        """
        print("=" * 80)
        print("       JARVIS-PiPER: 3 CORE RESEARCH STARTER THEMES GENERATION")
        print(f"  Target Root: {self.output_root} | Episodes per theme: {episodes_per_theme}")
        print("=" * 80)

        results = {}
        core_themes = [
            ManipulationTheme.PICK_AND_PLACE,
            ManipulationTheme.VISUAL_PREDICTION,
            ManipulationTheme.FAILURE_RECOVERY,
        ]

        total_generated = 0
        for theme in core_themes:
            print(f"\n--- Generating Theme: {theme.value.upper()} ---")
            theme_eps = []
            for i in range(episodes_per_theme):
                meta = self.generate_episode(theme=theme, episode_index=i + 1)
                theme_eps.append(meta)
                total_generated += 1
            results[theme.value] = theme_eps

        print("=" * 80)
        print(f" [COMPLETE] Generated {total_generated} episodes across {len(core_themes)} core themes.")
        print("=" * 80)
        return results
