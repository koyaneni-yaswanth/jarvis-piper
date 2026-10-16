"""
JARVIS-PiPER: High-Fidelity MuJoCo Simulation Environment.
Provides:
- Native MuJoCo physics stepping for AgileX PiPER 6-DOF arm & parallel gripper.
- Offscreen synthetic camera rendering (RGB & depth for wrist and overhead cameras).
- State telemetry (joint positions, velocities, TCP pose, cube tracking, contact state).
- Explicit data provenance labeling: DATA_ORIGIN = SIMULATION_MUJOCO.
- Support for passive GUI viewer and headless execution.
"""

import os
import sys
import time
import json
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import numpy as np

try:
    import mujoco
    import mujoco.viewer
    HAS_MUJOCO = True
except ImportError:
    HAS_MUJOCO = False

_repo_python = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "python"))
if _repo_python not in sys.path:
    sys.path.insert(0, _repo_python)

from world_model.spatial import PiperKinematics


class MuJoCoPiPEREnv:
    """
    MuJoCo Physics Simulation Environment for AgileX PiPER arm.
    """

    JOINT_NAMES = ["joint1", "joint2", "joint3", "joint4", "joint5", "joint6"]
    GRIPPER_ACTUATOR_NAMES = ["act_gripper_l", "act_gripper_r"]

    def __init__(
        self,
        xml_path: Optional[str] = None,
        control_dt: float = 0.02,  # 50 Hz control loop
        render_width: int = 320,
        render_height: int = 240,
    ):
        if not HAS_MUJOCO:
            raise RuntimeError("mujoco is not installed in the active environment.")

        if xml_path is None:
            repo_root = Path(__file__).resolve().parent.parent
            xml_path = str(repo_root / "assets" / "piper" / "piper.xml")

        self.xml_path = xml_path
        self.model = mujoco.MjModel.from_xml_path(self.xml_path)
        self.data = mujoco.MjData(self.model)

        self.control_dt = control_dt
        self.physics_timestep = self.model.opt.timestep
        self.substeps = max(1, int(round(self.control_dt / self.physics_timestep)))

        self.render_width = render_width
        self.render_height = render_height
        self._renderer: Optional[mujoco.Renderer] = None

        self.kinematics = PiperKinematics()
        self.joint_limits = self.kinematics.JOINT_LIMITS

        # Default home posture (radians)
        self.q_home = np.array([0.0, 0.40, -0.50, 0.0, 0.10, 0.0], dtype=np.float64)
        self.step_count = 0
        self.viewer = None

        self.reset()

    def reset(self, seed: Optional[int] = None) -> Dict[str, Any]:
        """Resets the simulation to the home posture with optional randomization."""
        if seed is not None:
            np.random.seed(seed)

        mujoco.mj_resetData(self.model, self.data)
        self.step_count = 0

        # Set arm joints to home posture
        for i, j_name in enumerate(self.JOINT_NAMES):
            j_id = mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_JOINT, j_name)
            qpos_adr = self.model.jnt_qposadr[j_id]
            self.data.qpos[qpos_adr] = self.q_home[i]

        # Reset red cube position on tabletop
        cube_body_id = mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_BODY, "red_cube")
        if cube_body_id != -1:
            jnt_adr = self.model.body_jntadr[cube_body_id]
            if jnt_adr != -1:
                qadr = self.model.jnt_qposadr[jnt_adr]
                # Default position [0.45, -0.08, 0.32] with slight noise if seed given
                dx = np.random.uniform(-0.02, 0.02) if seed is not None else 0.0
                dy = np.random.uniform(-0.02, 0.02) if seed is not None else 0.0
                self.data.qpos[qadr : qadr + 3] = [0.45 + dx, -0.08 + dy, 0.32]
                self.data.qpos[qadr + 3 : qadr + 7] = [1.0, 0.0, 0.0, 0.0]

        mujoco.mj_forward(self.model, self.data)
        return self.get_observation()

    def step(
        self,
        target_joint_pos: List[float],
        target_gripper_stroke: float = 0.035,
    ) -> Tuple[Dict[str, Any], float, bool, Dict[str, Any]]:
        """
        Executes one control cycle (multiple physics substeps).
        Applies clamped joint target positions and gripper stroke.
        """
        # Clamp commanded joints to physical boundaries
        clamped_targets = []
        for i, cmd in enumerate(target_joint_pos[:6]):
            lim_min, lim_max = self.joint_limits[i]
            clamped_targets.append(float(np.clip(cmd, lim_min, lim_max)))

        # Assign actuator control inputs
        for i in range(6):
            act_name = f"act_j{i+1}"
            act_id = mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_ACTUATOR, act_name)
            if act_id != -1:
                self.data.ctrl[act_id] = clamped_targets[i]

        # Gripper stroke [0.0, 0.035]m per finger
        finger_stroke = float(np.clip(target_gripper_stroke / 2.0, 0.0, 0.035))
        for act_name in self.GRIPPER_ACTUATOR_NAMES:
            act_id = mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_ACTUATOR, act_name)
            if act_id != -1:
                self.data.ctrl[act_id] = finger_stroke

        # Step physics forward
        for _ in range(self.substeps):
            mujoco.mj_step(self.model, self.data)

        self.step_count += 1
        obs = self.get_observation()

        # Check task metric: distance from TCP to red cube
        tcp_pos = np.array(obs["tcp_pose"]["position"])
        cube_pos = np.array(obs["cube_position"])
        dist_to_cube = float(np.linalg.norm(tcp_pos - cube_pos))

        reward = -dist_to_cube
        done = (self.step_count >= 200)

        info = {
            "step": self.step_count,
            "dist_to_cube_m": round(dist_to_cube, 4),
            "data_origin": "SIMULATION_MUJOCO",
        }
        return obs, reward, done, info

    def get_observation(self) -> Dict[str, Any]:
        """Reads instantaneous simulated robot observation state."""
        q_cur = []
        v_cur = []
        for j_name in self.JOINT_NAMES:
            j_id = mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_JOINT, j_name)
            qpos_adr = self.model.jnt_qposadr[j_id]
            qvel_adr = self.model.jnt_dofadr[j_id]
            q_cur.append(float(self.data.qpos[qpos_adr]))
            v_cur.append(float(self.data.qvel[qvel_adr]))

        # Read TCP position & orientation (relative to base_link)
        base_id = mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_BODY, "base_link")
        base_pos = self.data.xpos[base_id] if base_id != -1 else np.zeros(3)
        site_id = mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_SITE, "tcp_site")
        if site_id != -1:
            tcp_pos = (self.data.site_xpos[site_id] - base_pos).tolist()
            tcp_mat = self.data.site_xmat[site_id].reshape(3, 3)
            # Convert rotation matrix to quaternion [x, y, z, w]
            quat = np.zeros(4)
            mujoco.mju_mat2Quat(quat, tcp_mat.flatten())
            tcp_quat = [float(quat[1]), float(quat[2]), float(quat[3]), float(quat[0])]
        else:
            tcp_pos, _ = self.kinematics.compute_fk(q_cur)
            tcp_quat = [0.0, 0.0, 0.0, 1.0]

        # Read cube position
        cube_id = mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_BODY, "red_cube")
        if cube_id != -1:
            cube_pos = self.data.xpos[cube_id].tolist()
        else:
            cube_pos = [0.45, -0.08, 0.32]

        # Read finger position
        grp_j_id = mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_JOINT, "gripper_left")
        gripper_stroke = float(self.data.qpos[self.model.jnt_qposadr[grp_j_id]] * 2.0) if grp_j_id != -1 else 0.0

        return {
            "joint_positions": [round(x, 5) for x in q_cur],
            "joint_velocities": [round(v, 5) for v in v_cur],
            "tcp_pose": {
                "position": [round(x, 5) for x in tcp_pos],
                "quaternion": [round(x, 5) for x in tcp_quat],
            },
            "gripper_stroke": round(gripper_stroke, 5),
            "cube_position": [round(x, 5) for x in cube_pos],
            "sim_time": round(float(self.data.time), 4),
            "step_count": self.step_count,
            "data_origin": "SIMULATION_MUJOCO",
        }

    def render_camera(self, camera_name: str = "wrist_camera", depth: bool = False) -> np.ndarray:
        """Renders an offscreen synthetic camera frame from the MuJoCo scene."""
        if self._renderer is None:
            self._renderer = mujoco.Renderer(self.model, self.render_height, self.render_width)

        if depth:
            self._renderer.enable_depth_rendering()
        else:
            self._renderer.disable_depth_rendering()

        self._renderer.update_scene(self.data, camera=camera_name)
        frame = self._renderer.render()
        return frame

    def launch_passive_viewer(self):
        """Launches the interactive MuJoCo passive viewer window if DISPLAY is available."""
        if not os.environ.get("DISPLAY") and not os.environ.get("WAYLAND_DISPLAY"):
            print("[WARN] No graphical display detected. Skipping interactive viewer.")
            return None
        try:
            self.viewer = mujoco.viewer.launch_passive(self.model, self.data)
            print("[INFO] MuJoCo passive viewer launched.")
            return self.viewer
        except Exception as e:
            print(f"[WARN] Could not launch passive viewer: {e}")
            return None

    def sync_viewer(self):
        """Updates passive viewer display if active."""
        if self.viewer is not None and self.viewer.is_running():
            self.viewer.sync()

    def close(self):
        """Releases renderer and closes viewer."""
        if self._renderer is not None:
            self._renderer.close()
            self._renderer = None
        if self.viewer is not None:
            try:
                self.viewer.close()
            except Exception:
                pass
            self.viewer = None
