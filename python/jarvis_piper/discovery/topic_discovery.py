"""
Automatic Topic Discovery & Candidate Mapping for JARVIS-PiPER.
Discovers active camera, arm, gripper, and teleoperation topics without hardcoding.
"""

import os
import shutil
import subprocess
from typing import Dict, List
import yaml


class TopicDiscovery:
    """Discovers candidate topics from the live ROS 2 system."""

    def __init__(self):
        self.ros_available = shutil.which("ros2") is not None

    def discover_topics(self) -> Dict[str, List[str]]:
        """Queries ROS 2 and maps topics to candidate roles."""
        candidates = {
            "joint_states": [],
            "cameras_rgb": [],
            "cameras_depth": [],
            "teleoperation": [],
            "gripper": [],
            "tf": [],
            "imu": [],
        }

        if not self.ros_available:
            # Fallback to standard defaults
            candidates["joint_states"].append("/joint_states")
            candidates["cameras_rgb"].extend(["/camera", "/camera/color/image_raw"])
            candidates["cameras_depth"].extend(["/camera/depth_image", "/camera/depth/image_rect_raw"])
            candidates["teleoperation"].append("/pika_pose")
            candidates["gripper"].extend(["/gripper/ctrl", "/gripper/data"])
            candidates["tf"].extend(["/tf", "/tf_static"])
            candidates["imu"].extend(["/imu", "/imu/data"])
            return candidates

        try:
            res = subprocess.run(
                ["ros2", "topic", "list", "-t"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            for line in res.stdout.strip().splitlines():
                if not line.strip():
                    continue
                parts = line.strip().split()
                topic_name = parts[0]
                msg_type = parts[1].strip("[]") if len(parts) > 1 else ""

                if "JointState" in msg_type or "joint" in topic_name:
                    candidates["joint_states"].append(topic_name)
                if "Image" in msg_type:
                    if "depth" in topic_name:
                        candidates["cameras_depth"].append(topic_name)
                    else:
                        candidates["cameras_rgb"].append(topic_name)
                if "pika" in topic_name or "PoseStamped" in msg_type:
                    candidates["teleoperation"].append(topic_name)
                if "gripper" in topic_name:
                    candidates["gripper"].append(topic_name)
                if "tf" in topic_name:
                    candidates["tf"].append(topic_name)
                if "Imu" in msg_type:
                    candidates["imu"].append(topic_name)
        except Exception:
            pass

        return candidates

    def generate_config(self, output_path: str = "configs/generated_topics.yaml") -> Dict[str, str]:
        """Saves discovered topic mappings to YAML."""
        cand = self.discover_topics()
        mapping = {
            "joint_states": cand["joint_states"][0] if cand["joint_states"] else "/joint_states",
            "camera_rgb": cand["cameras_rgb"][0] if cand["cameras_rgb"] else "/camera",
            "camera_depth": cand["cameras_depth"][0] if cand["cameras_depth"] else "/camera/depth_image",
            "teleoperation_pose": cand["teleoperation"][0] if cand["teleoperation"] else "/pika_pose",
            "gripper_ctrl": cand["gripper"][0] if cand["gripper"] else "/gripper/ctrl",
        }

        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            yaml.dump({"discovered_topics": mapping}, f, default_flow_style=False)

        return mapping
