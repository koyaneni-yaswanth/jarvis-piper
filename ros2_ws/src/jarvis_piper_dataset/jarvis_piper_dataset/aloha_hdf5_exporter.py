"""
ALOHA / ACT / Diffusion Policy Dataset Exporter for JARVIS PiPER.
Produces HDF5 / NPZ datasets matching the canonical ALOHA training schema:
qpos [T, 8], qvel [T, 8], action [T, 8], observations/images.
"""

import os
from typing import Any, Dict, List
import numpy as np

try:
    import h5py
    HAS_H5PY = True
except ImportError:
    HAS_H5PY = False


class AlohaHdf5Exporter:
    """Exports episodes to ALOHA / ACT compatible HDF5 and tensor archives."""

    def __init__(self, output_dir: str):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    def export_episode(self, episode_data: Dict[str, Any], ep_index: int = 0) -> str:
        """Exports a single episode into ALOHA HDF5 / NPZ format."""
        meta = episode_data.get("metadata", {})
        steps = episode_data.get("timesteps", [])
        ep_id = meta.get("episode_id", f"episode_{ep_index:06d}")
        T = len(steps)

        # 8-dimensional ALOHA state: [base_yaw, piper_joint1..6, gripper_stroke]
        qpos = np.zeros((T, 8), dtype=np.float32)
        qvel = np.zeros((T, 8), dtype=np.float32)
        effort = np.zeros((T, 8), dtype=np.float32)
        action = np.zeros((T, 8), dtype=np.float32)

        for t, step in enumerate(steps):
            q = step.get("joint_positions", [0.0] * 6)[:6]
            v = step.get("joint_velocities", [0.0] * 6)[:6]
            eff = step.get("joint_efforts", [0.0] * 6)[:6]
            stroke = step.get("gripper_stroke", 0.035)

            qpos[t, 1:7] = q
            qpos[t, 7] = stroke

            qvel[t, 1:7] = v
            effort[t, 1:7] = eff

            act = step.get("action", q)[:6]
            action[t, 1:7] = act
            action[t, 7] = stroke

        if HAS_H5PY:
            file_path = os.path.join(self.output_dir, f"{ep_id}.hdf5")
            with h5py.File(file_path, "w") as root:
                root.attrs["sim"] = True
                root.attrs["task_instruction"] = meta.get("task_instruction", "")
                root.attrs["episode_id"] = ep_id
                root.attrs["success"] = meta.get("success_label", True)

                root.create_dataset("action", data=action)
                obs_grp = root.create_group("observations")
                obs_grp.create_dataset("qpos", data=qpos)
                obs_grp.create_dataset("qvel", data=qvel)
                obs_grp.create_dataset("effort", data=effort)

                # Images placeholder
                img_grp = obs_grp.create_group("images")
                img_grp.create_dataset("wrist_cam", shape=(T, 1, 1, 3), dtype=np.uint8)
                img_grp.create_dataset("top_cam", shape=(T, 1, 1, 3), dtype=np.uint8)
            return file_path
        else:
            # Fallback to ALOHA-structured NPZ archive
            file_path = os.path.join(self.output_dir, f"{ep_id}.npz")
            np.savez_compressed(
                file_path,
                action=action,
                qpos=qpos,
                qvel=qvel,
                effort=effort,
                episode_id=ep_id,
                task_instruction=meta.get("task_instruction", ""),
                success=meta.get("success_label", True),
                timesteps=T,
            )
            return file_path

    def export_dataset(self, episodes_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        exported_files = []
        for i, ep in enumerate(episodes_data):
            fpath = self.export_episode(ep, i)
            exported_files.append(fpath)

        return {
            "status": "success",
            "format": "aloha_hdf5" if HAS_H5PY else "aloha_npz",
            "output_dir": self.output_dir,
            "total_episodes": len(episodes_data),
            "files": exported_files,
        }
