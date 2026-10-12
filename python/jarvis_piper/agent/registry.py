"""
JARVIS Skill & Capability Registry.
Maintains validated robotic skills, preconditions, hardware requirements, and health statuses:
AVAILABLE, DEGRADED, UNAVAILABLE, BUSY, UNSAFE.
"""

from typing import Any, Callable, Dict, List, Optional


class SkillStatus:
    AVAILABLE = "AVAILABLE"
    DEGRADED = "DEGRADED"
    UNAVAILABLE = "UNAVAILABLE"
    BUSY = "BUSY"
    UNSAFE = "UNSAFE"


class CapabilityRegistry:
    """Manages registered embodied skills and verifies system prerequisites."""

    def __init__(self):
        self._skills: Dict[str, Dict[str, Any]] = {}
        self._register_default_skills()

    def _register_default_skills(self):
        self.register_skill(
            name="pick_and_place",
            description="Picks up a localized object and places it at target destination.",
            required_sensors=["camera", "joint_states", "gripper_feedback"],
            required_controllers=["arm_trajectory_controller", "gripper_controller"],
            workspace_limits={"x": (0.15, 0.55), "y": (-0.40, 0.40), "z": (0.02, 0.50)},
            timeout_s=30.0,
            status=SkillStatus.AVAILABLE,
        )
        self.register_skill(
            name="reach_target",
            description="Moves the TCP to a target 3D Cartesian position.",
            required_sensors=["joint_states"],
            required_controllers=["arm_trajectory_controller"],
            workspace_limits={"x": (0.15, 0.60), "y": (-0.45, 0.45), "z": (0.05, 0.55)},
            timeout_s=10.0,
            status=SkillStatus.AVAILABLE,
        )
        self.register_skill(
            name="teleoperate",
            description="Streams PIKA Sense hand poses to Piper manipulator.",
            required_sensors=["pika_pose", "joint_states"],
            required_controllers=["arm_trajectory_controller"],
            workspace_limits={"x": (0.10, 0.60), "y": (-0.45, 0.45), "z": (0.02, 0.55)},
            timeout_s=300.0,
            status=SkillStatus.AVAILABLE,
        )
        self.register_skill(
            name="home_pose",
            description="Moves manipulator to safe upright home configuration.",
            required_sensors=["joint_states"],
            required_controllers=["arm_trajectory_controller"],
            workspace_limits={"x": (0.0, 0.60), "y": (-0.45, 0.45), "z": (0.0, 0.60)},
            timeout_s=5.0,
            status=SkillStatus.AVAILABLE,
        )

    def register_skill(
        self,
        name: str,
        description: str,
        required_sensors: List[str],
        required_controllers: List[str],
        workspace_limits: Dict[str, Any],
        timeout_s: float,
        status: str = SkillStatus.AVAILABLE,
    ):
        self._skills[name] = {
            "name": name,
            "description": description,
            "required_sensors": required_sensors,
            "required_controllers": required_controllers,
            "workspace_limits": workspace_limits,
            "timeout_s": timeout_s,
            "status": status,
        }

    def get_skill(self, name: str) -> Optional[Dict[str, Any]]:
        return self._skills.get(name)

    def is_skill_available(self, name: str) -> bool:
        skill = self._skills.get(name)
        return skill is not None and skill["status"] == SkillStatus.AVAILABLE

    def list_capabilities(self) -> Dict[str, str]:
        return {name: info["status"] for name, info in self._skills.items()}
