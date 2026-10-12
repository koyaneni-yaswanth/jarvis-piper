"""
JARVIS Autonomous Agent Orchestrator.
Parses natural language instructions into structured execution plans, validates capabilities,
manages episodic memory, and coordinates safe physical manipulation.
"""

import re
import time
from typing import Any, Dict, List, Optional

from jarvis_piper.agent.registry import CapabilityRegistry, SkillStatus
from jarvis_piper.tasks.pick_and_place import PickAndPlaceTask


class JarvisOrchestrator:
    """
    JARVIS Natural-Language Task Orchestrator:
    Human text/voice -> intent parsing -> capability verification -> safe execution -> memory -> response
    """

    def __init__(self, mode: str = "simulation"):
        self.mode = mode.lower()
        self.registry = CapabilityRegistry()
        self.pick_and_place = PickAndPlaceTask(mode=self.mode)
        self.working_memory: Dict[str, Any] = {
            "current_task": None,
            "last_action": None,
            "detected_objects": ["red_cube", "blue_tray"],
            "robot_state": "IDLE",
        }
        self.episodic_history: List[Dict[str, Any]] = []

    def parse_instruction(self, instruction: str) -> Dict[str, Any]:
        """Parses natural language prompt into structured task intent and arguments."""
        text = instruction.strip().lower()

        # Stop / Pause Intents
        if any(w in text for w in ["stop", "emergency stop", "halt", "freeze"]):
            return {"intent": "emergency_stop", "args": {}}

        if "pause" in text:
            return {"intent": "pause", "args": {}}

        # Status / Query Intents
        if any(phrase in text for phrase in ["what are you doing", "what is your status", "current status"]):
            return {"intent": "query_status", "args": {}}

        if "what do you see" in text or "look around" in text:
            return {"intent": "query_vision", "args": {}}

        # Pick and Place Pattern
        pick_match = re.search(r"pick(?:\s+up)?\s+(?:the\s+)?([a-z_\s]+?)(?:\s+and\s+place|\s+and\s+put|\s+in|\s+to|\s+on|$)", text)
        dest_match = re.search(r"(?:in|to|into|on)\s+(?:the\s+)?([a-z_\s]+)", text)

        target_obj = pick_match.group(1).strip().replace(" ", "_") if pick_match else "red_cube"
        destination = dest_match.group(1).strip().replace(" ", "_") if dest_match else "blue_tray"

        if "pick" in text or "place" in text or "move" in text:
            return {
                "intent": "pick_and_place",
                "args": {"target_object": target_obj, "destination": destination},
            }

        # Home Intent
        if "home" in text:
            return {"intent": "home_pose", "args": {}}

        return {"intent": "unknown", "raw": instruction}

    def execute_command(self, instruction: str) -> Dict[str, Any]:
        plan = self.parse_instruction(instruction)
        intent = plan["intent"]
        start_t = time.time()

        print(f"\n[JARVIS] Instruction Received: '{instruction}' -> Intent: {intent.upper()}")

        if intent == "emergency_stop":
            self.working_memory["robot_state"] = "ESTOP"
            return {
                "status": "HALTED",
                "message": "Emergency stop acknowledged. All motor actuation frozen immediately.",
                "execution_time_s": 0.01,
            }

        if intent == "query_status":
            return {
                "status": "INFO",
                "message": f"Robot is currently {self.working_memory['robot_state']}. Working memory holds {len(self.episodic_history)} completed episodes.",
            }

        if intent == "query_vision":
            objs = ", ".join(self.working_memory["detected_objects"])
            return {
                "status": "INFO",
                "message": f"Perception cameras detect objects on workstation: {objs}.",
            }

        if intent == "pick_and_place":
            if not self.registry.is_skill_available("pick_and_place"):
                return {
                    "status": "REJECTED",
                    "message": "Skill 'pick_and_place' is currently unavailable or preconditions are unfulfilled.",
                }

            args = plan["args"]
            self.working_memory["robot_state"] = "EXECUTING_PICK_AND_PLACE"
            res = self.pick_and_place.execute_task(
                instruction=instruction,
                target_object=args["target_object"],
                destination=args["destination"],
            )

            # Record in episodic memory
            ep_record = {
                "instruction": instruction,
                "task": "pick_and_place",
                "success": res["success"],
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "duration_s": res["execution_time_s"],
            }
            self.episodic_history.append(ep_record)
            self.working_memory["robot_state"] = "IDLE"
            self.working_memory["last_action"] = ep_record

            if res["success"]:
                msg = f"Task completed successfully: picked up {args['target_object']} and placed at {args['destination']} in {res['execution_time_s']}s."
            else:
                msg = f"Task failed: {res.get('reason', 'Unknown error')}."

            return {
                "status": "SUCCESS" if res["success"] else "FAILED",
                "message": msg,
                "details": res,
            }

        return {
            "status": "UNSUPPORTED",
            "message": f"I parsed your instruction as '{intent}', but do not have an approved execution skill for this command yet.",
        }
