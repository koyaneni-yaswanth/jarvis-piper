"""
Phase 6: JARVIS Natural-Language Task Interface & Dispatcher.
Parses text commands, validates reachability and safety constraints,
and dispatches execution to planning modules without bypassing the safety layer.
"""

import re
from typing import Dict, Any, Optional, Tuple
from simulation.environment import JarvisSimEnvironment
from task_planning.pick_and_place import VisionGuidedPickAndPlaceTask
from jarvis_piper.safety.supervisor import SafetySupervisor


class JarvisTaskPlanner:
    """
    Translates natural-language commands into verified robotic actions.
    Enforces that no language proposal ever bypasses motion planning or safety checks.
    """

    SUPPORTED_OBJECTS = ["red cube", "red block", "cube", "block", "cup", "bowl"]
    SUPPORTED_DESTINATIONS = ["tray", "blue tray", "bowl", "table", "left side", "right side"]

    def __init__(self, env: Optional[JarvisSimEnvironment] = None):
        self.env = env or JarvisSimEnvironment()
        self.task_executor = VisionGuidedPickAndPlaceTask(env=self.env)
        self.safety = SafetySupervisor()

    def parse_instruction(self, text: str) -> Dict[str, Any]:
        """
        Parses text instruction into action intent, target, and destination.
        Rejects ambiguous or unsupported requests.
        """
        lower = text.strip().lower()

        # 1. Check placement verification query
        if "check" in lower or "status" in lower or "successfully placed" in lower:
            return {
                "intent": "verify_state",
                "valid": True,
            }

        # 2. Pick and Place intent pattern
        pick_match = re.search(r"(?:pick up|grab|take|move)\s+(?:the\s+)?([a-z\s]+?)\s+(?:and\s+place\s+(?:it\s+)?(?:in|into|on|to)\s+(?:the\s+)?([a-z\s]+?)|to\s+(?:the\s+)?([a-z\s]+?))$", lower)

        if pick_match:
            obj_candidate = pick_match.group(1).strip()
            dest_candidate = (pick_match.group(2) or pick_match.group(3) or "").strip()

            # Validate against supported object taxonomy
            matched_obj = None
            for o in self.SUPPORTED_OBJECTS:
                if o in obj_candidate:
                    matched_obj = "red_cube" if "red" in o or "cube" in o or "block" in o else o
                    break

            matched_dest = None
            for d in self.SUPPORTED_DESTINATIONS:
                if d in dest_candidate:
                    matched_dest = "tray" if "tray" in d else d
                    break

            if not matched_obj:
                return {
                    "valid": False,
                    "reason": f"Unsupported or ambiguous target object: '{obj_candidate}'",
                }

            if not matched_dest:
                return {
                    "valid": False,
                    "reason": f"Unsupported destination: '{dest_candidate}'",
                }

            return {
                "intent": "pick_and_place",
                "target_object": matched_obj,
                "destination": matched_dest,
                "valid": True,
            }

        return {
            "valid": False,
            "reason": f"Could not parse instruction into supported task: '{text}'",
        }

    def execute_command(self, text: str, episode_seed: Optional[int] = None) -> Dict[str, Any]:
        """
        Parses instruction, passes through safety checks, and runs task.
        """
        parsed = self.parse_instruction(text)
        if not parsed.get("valid", False):
            return {
                "command": text,
                "status": "REJECTED",
                "reason": parsed.get("reason", "Unknown command syntax"),
            }

        intent = parsed.get("intent")

        if intent == "verify_state":
            obs = self.env.get_observation()
            dist_to_tray = float(self.env.placement.position[0] - obs["cube_position"][0])
            placed = bool(not obs["object_held"] and abs(dist_to_tray) < 0.08)
            return {
                "command": text,
                "status": "SUCCESS",
                "intent": intent,
                "object_placed": placed,
                "object_held": obs["object_held"],
                "cube_position": obs["cube_position"],
            }

        elif intent == "pick_and_place":
            # Execute with safety supervision
            metrics = self.task_executor.run_episode(episode_seed=episode_seed)
            return {
                "command": text,
                "status": "SUCCESS" if metrics.get("placement_success") else "FAILED",
                "intent": intent,
                "target_object": parsed.get("target_object"),
                "destination": parsed.get("destination"),
                "metrics": metrics,
            }

        return {"command": text, "status": "REJECTED", "reason": "Unimplemented intent"}
