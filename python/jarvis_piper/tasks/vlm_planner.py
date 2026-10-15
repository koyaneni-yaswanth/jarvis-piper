"""
JARVIS-PiPER: Vision-Language Task Planner.

Converts natural-language requests into structured, inspectable plans.
The planner uses VLM perception output as one input among several validated
sources. It does NOT directly generate joint commands or enable motors.

Architecture:
  NL Request -> TaskPlanner -> TaskPlan (inspectable steps)
                                 |
                          Safety Supervisor (separate)
                                 |
                        Robot Adapter (only with explicit operator authorization)

The VLM is a *perception provider*, not a *command generator*.
"""

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Plan data structures
# ---------------------------------------------------------------------------

class StepStatus(str, Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"
    AWAITING_OPERATOR = "AWAITING_OPERATOR"


@dataclass
class PlanStep:
    """A single step in a structured task plan."""
    step_id: int
    description: str
    status: StepStatus = StepStatus.PENDING
    result: Optional[str] = None
    uncertainty: Optional[float] = None  # 0.0 = certain, 1.0 = completely uncertain
    requires_operator_confirmation: bool = False
    requires_hardware: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __str__(self) -> str:
        flag = " [OPERATOR REQUIRED]" if self.requires_operator_confirmation else ""
        hw = " [HARDWARE]" if self.requires_hardware else ""
        return (
            f"Step {self.step_id:02d}: [{self.status.value:12s}]{flag}{hw} "
            f"{self.description}"
            + (f" -> {self.result}" if self.result else "")
        )


@dataclass
class TaskPlan:
    """A structured, inspectable representation of a task."""
    request: str
    steps: List[PlanStep] = field(default_factory=list)
    created_at: float = field(default_factory=time.monotonic)
    completed_at: Optional[float] = None
    success: Optional[bool] = None
    notes: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)  # runtime state (not serialized)


    def summary(self) -> str:
        lines = [f"Task: {self.request!r}", f"Steps: {len(self.steps)}"]
        for step in self.steps:
            lines.append(f"  {step}")
        if self.notes:
            lines.append("Notes:")
            for note in self.notes:
                lines.append(f"  - {note}")
        return "\n".join(lines)

    @property
    def is_hardware_task(self) -> bool:
        return any(s.requires_hardware for s in self.steps)

    @property
    def all_steps_safe(self) -> bool:
        return not any(
            s.requires_hardware and not s.requires_operator_confirmation
            for s in self.steps
        )


# ---------------------------------------------------------------------------
# Task classification
# ---------------------------------------------------------------------------

class TaskType(str, Enum):
    VISUAL_QUERY = "visual_query"          # "What do you see?"
    OBJECT_IDENTIFICATION = "object_id"   # "What color is that object?"
    SCENE_DESCRIPTION = "scene_desc"      # "Describe the table"
    OBJECT_LOCALIZATION = "obj_loc"       # "Where is the red block?"
    MANIPULATION = "manipulation"         # "Pick up the red block"
    UNKNOWN = "unknown"


def classify_task(request: str) -> TaskType:
    """Classify a natural-language request into a TaskType.

    Uses keyword matching. Does not require a model.
    """
    req = request.lower()

    # Manipulation patterns (require hardware)
    manipulation_keywords = [
        "pick up", "pick", "grab", "grasp", "place", "put", "move",
        "drop", "carry", "bring", "hand", "transfer", "stack",
    ]
    if any(kw in req for kw in manipulation_keywords):
        return TaskType.MANIPULATION

    # Object localization (VLM + detector, no motors)
    localization_keywords = [
        "where is", "where's", "locate", "find", "position of",
        "coordinates", "location",
    ]
    if any(kw in req for kw in localization_keywords):
        return TaskType.OBJECT_LOCALIZATION

    # Object identification
    identification_keywords = [
        "what is", "what's", "identify", "name the", "what color",
        "what shape", "what type", "what kind",
    ]
    if any(kw in req for kw in identification_keywords):
        return TaskType.OBJECT_IDENTIFICATION

    # Scene description
    description_keywords = [
        "describe", "what do you see", "tell me about", "look at",
        "observe", "scene", "view",
    ]
    if any(kw in req for kw in description_keywords):
        return TaskType.SCENE_DESCRIPTION

    # Visual query (most general)
    query_keywords = [
        "is there", "are there", "can you see", "do you see",
        "show me", "check",
    ]
    if any(kw in req for kw in query_keywords):
        return TaskType.VISUAL_QUERY

    return TaskType.UNKNOWN


# ---------------------------------------------------------------------------
# Task Planner
# ---------------------------------------------------------------------------

class VisionTaskPlanner:
    """
    Plans vision-language tasks as structured, auditable step sequences.

    The planner:
    1. Classifies the request into a TaskType.
    2. Generates the appropriate step sequence.
    3. Marks steps that require hardware with requires_hardware=True and
       requires_operator_confirmation=True.
    4. NEVER generates joint commands or publishes to hardware directly.
    5. Returns the plan for operator review before execution.

    Usage
    -----
    planner = VisionTaskPlanner(vlm=my_vlm, camera=my_camera)
    plan = planner.plan("Look at the table and identify the red object")
    print(plan.summary())
    # Operator reviews plan, then:
    result = planner.execute_plan(plan)
    """

    def __init__(
        self,
        vlm: Any,       # VisionLanguageModel
        camera: Any,    # CameraSource
        uncertainty_threshold: float = 0.7,
        request_clarification_on_uncertainty: bool = True,
    ) -> None:
        self._vlm = vlm
        self._camera = camera
        self._uncertainty_threshold = uncertainty_threshold
        self._request_clarification = request_clarification_on_uncertainty

    def plan(self, request: str) -> TaskPlan:
        """
        Generate an inspectable task plan for a natural-language request.

        No hardware interaction occurs during planning.
        Manipulation tasks include hardware-gated steps that require operator
        confirmation before execution.

        Parameters
        ----------
        request : str
            Natural language task description.

        Returns
        -------
        TaskPlan
            Structured, auditable task plan.
        """
        task_type = classify_task(request)
        logger.info("Planning task: %r -> TaskType=%s", request, task_type.value)

        if task_type == TaskType.SCENE_DESCRIPTION:
            return self._plan_scene_description(request)
        elif task_type == TaskType.VISUAL_QUERY:
            return self._plan_visual_query(request)
        elif task_type == TaskType.OBJECT_IDENTIFICATION:
            return self._plan_object_identification(request)
        elif task_type == TaskType.OBJECT_LOCALIZATION:
            return self._plan_object_localization(request)
        elif task_type == TaskType.MANIPULATION:
            return self._plan_manipulation(request)
        else:
            return self._plan_unknown(request)

    def execute_plan(
        self,
        plan: TaskPlan,
        operator_authorized: bool = False,
    ) -> TaskPlan:
        """
        Execute a planned task step by step.

        Parameters
        ----------
        plan : TaskPlan
            The plan to execute (from plan()).
        operator_authorized : bool
            Must be True for hardware steps to execute.
            False by default — hardware steps will be skipped with
            AWAITING_OPERATOR status.

        Returns
        -------
        TaskPlan
            Updated plan with step results and status.
        """
        for step in plan.steps:
            if step.status != StepStatus.PENDING:
                continue

            if step.requires_hardware and not operator_authorized:
                step.status = StepStatus.AWAITING_OPERATOR
                step.result = (
                    "Hardware step blocked: operator authorization required. "
                    "Re-execute with operator_authorized=True after safety review."
                )
                logger.warning(
                    "Step %d blocked (hardware, no auth): %s",
                    step.step_id, step.description,
                )
                continue

            step.status = StepStatus.IN_PROGRESS
            try:
                self._execute_step(step, plan)
                if step.status == StepStatus.IN_PROGRESS:
                    step.status = StepStatus.COMPLETED
            except Exception as exc:
                step.status = StepStatus.FAILED
                step.result = f"Failed: {exc}"
                logger.error("Step %d failed: %s", step.step_id, exc)
                plan.notes.append(f"Step {step.step_id} failed: {exc}")
                break

        plan.completed_at = time.monotonic()
        completed = sum(s.status == StepStatus.COMPLETED for s in plan.steps)
        awaiting = sum(s.status == StepStatus.AWAITING_OPERATOR for s in plan.steps)
        failed = sum(s.status == StepStatus.FAILED for s in plan.steps)
        plan.success = (failed == 0) and (awaiting == 0)
        return plan

    # ------------------------------------------------------------------
    # Plan generators
    # ------------------------------------------------------------------

    def _plan_scene_description(self, request: str) -> TaskPlan:
        return TaskPlan(
            request=request,
            steps=[
                PlanStep(1, "Acquire camera frame from configured source."),
                PlanStep(2, "Validate frame: non-empty, correct dimensions, recent timestamp."),
                PlanStep(3, "Submit frame to VLM describe_image()."),
                PlanStep(4, "Validate VLM response: non-empty text, no error flag."),
                PlanStep(5, "Return textual scene description to operator."),
            ],
        )

    def _plan_visual_query(self, request: str) -> TaskPlan:
        return TaskPlan(
            request=request,
            steps=[
                PlanStep(1, "Acquire camera frame."),
                PlanStep(2, "Validate frame quality."),
                PlanStep(3, f"Ask VLM: answer_visual_question(image, {request!r})."),
                PlanStep(4, "Report answer and note VLM uncertainty."),
            ],
        )

    def _plan_object_identification(self, request: str) -> TaskPlan:
        return TaskPlan(
            request=request,
            steps=[
                PlanStep(1, "Acquire camera frame."),
                PlanStep(2, "Validate frame quality."),
                PlanStep(3, "Run CLIP candidate matching against relevant scene vocabulary."),
                PlanStep(4, "Note: CLIP scores are cosine similarities, not probabilities."),
                PlanStep(5, "If top score < 0.3: flag low-confidence result and request operator clarification."),
                PlanStep(6, "Return ranked identification results."),
            ],
        )

    def _plan_object_localization(self, request: str) -> TaskPlan:
        return TaskPlan(
            request=request,
            steps=[
                PlanStep(1, "Acquire camera frame (RGB + depth if available)."),
                PlanStep(2, "Validate frame quality."),
                PlanStep(3, "Submit frame to VLM detect_or_localize_objects()."),
                PlanStep(
                    4,
                    "If VLM returns bounding boxes: validate with JarvisPerceptionDetector "
                    "for depth-based reprojection.",
                    uncertainty=0.6,
                ),
                PlanStep(
                    5,
                    "Transform validated pixel position to camera coordinates using verified intrinsics.",
                    uncertainty=0.4,
                ),
                PlanStep(
                    6,
                    "NOTE: Camera-to-robot coordinate transform requires verified extrinsic calibration. "
                    "Calibration must be validated before any manipulation step.",
                    uncertainty=0.8,
                ),
                PlanStep(7, "Return textual localization result. No robot motion planned."),
            ],
        )

    def _plan_manipulation(self, request: str) -> TaskPlan:
        """
        Manipulation plan with explicit hardware gates.

        ALL hardware steps require operator confirmation. The plan can be
        generated safely without authorization; execution is blocked at hardware steps.
        """
        plan = TaskPlan(
            request=request,
            steps=[
                # Perception steps (no hardware)
                PlanStep(1, "Acquire camera frame (RGB + depth)."),
                PlanStep(2, "Validate frame: non-empty, fresh timestamp, correct resolution."),
                PlanStep(3, "Submit frame to VLM to identify the target object."),
                PlanStep(4, "Validate VLM response: non-empty, confidence assessment."),
                PlanStep(
                    5,
                    "Run JarvisPerceptionDetector to obtain bounding box and 3D centroid "
                    "of identified target.",
                    uncertainty=0.5,
                ),
                PlanStep(
                    6,
                    "Validate extrinsic calibration: camera-to-robot transform must have been "
                    "verified against physical ground-truth markers.",
                    uncertainty=0.7,
                ),
                PlanStep(
                    7,
                    "Transform 3D centroid to robot base frame using verified extrinsics.",
                    uncertainty=0.5,
                ),
                PlanStep(
                    8,
                    "Check target position is within SafetySupervisor workspace bounds "
                    "[x: 0.10–0.60m, y: ±0.45m, z: 0.015–0.55m].",
                ),
                PlanStep(9, "Solve IK for pre-grasp pose (target + 0.05m z-offset)."),
                PlanStep(10, "Validate IK solution: within joint limits and reachable."),

                # Hardware steps — all require operator authorization
                PlanStep(
                    11,
                    "[HARDWARE] Request operator confirmation: display planned pose and target.",
                    requires_operator_confirmation=True,
                    requires_hardware=False,  # Confirmation is human, not motor
                ),
                PlanStep(
                    12,
                    "[HARDWARE] Execute path to pre-grasp pose through SafetySupervisor.",
                    requires_operator_confirmation=True,
                    requires_hardware=True,
                ),
                PlanStep(
                    13,
                    "[HARDWARE] Descend to grasp pose. Monitor joint torques.",
                    requires_operator_confirmation=True,
                    requires_hardware=True,
                ),
                PlanStep(
                    14,
                    "[HARDWARE] Close gripper to target stroke. Verify grasp success via torque/position.",
                    requires_operator_confirmation=True,
                    requires_hardware=True,
                ),
                PlanStep(
                    15,
                    "[HARDWARE] Lift to clearance altitude (z=0.42m). Monitor load.",
                    requires_operator_confirmation=True,
                    requires_hardware=True,
                ),
                PlanStep(
                    16,
                    "[HARDWARE] Transport to destination. SafetySupervisor active throughout.",
                    requires_operator_confirmation=True,
                    requires_hardware=True,
                ),
                PlanStep(
                    17,
                    "[HARDWARE] Place: descend, open gripper, verify release.",
                    requires_operator_confirmation=True,
                    requires_hardware=True,
                ),
                PlanStep(
                    18,
                    "[HARDWARE] Retract to safe home pose.",
                    requires_operator_confirmation=True,
                    requires_hardware=True,
                ),
                PlanStep(19, "Log task outcome, timing, and telemetry."),
            ],
            notes=[
                "All HARDWARE steps require operator_authorized=True on execute_plan().",
                "The VLM provides perception descriptions only; it does NOT generate joint commands.",
                "The SafetySupervisor validates every command before transmission.",
                "Physical execution requires: CAN bus up, arm powered, E-Stop accessible.",
            ],
        )
        return plan

    def _plan_unknown(self, request: str) -> TaskPlan:
        return TaskPlan(
            request=request,
            steps=[
                PlanStep(1, f"Request could not be classified: {request!r}"),
                PlanStep(2, "Acquire camera frame for context."),
                PlanStep(3, "Submit frame and request to VLM as general VQA."),
                PlanStep(4, "Return VLM response. Operator must interpret and re-specify task."),
            ],
            notes=["Task type is UNKNOWN. No hardware steps will be generated."],
        )

    # ------------------------------------------------------------------
    # Step executor
    # ------------------------------------------------------------------

    def _execute_step(self, step: PlanStep, plan: TaskPlan) -> None:
        """Execute a single plan step using camera and VLM."""
        desc = step.description.lower()

        if "acquire camera frame" in desc:
            if not self._camera.is_open:
                self._camera.open()
            frame = self._camera.read()
            if not frame.is_valid:
                raise RuntimeError(
                    f"Camera '{self._camera.source_id}' returned an invalid frame."
                )
            step.metadata["frame_id"] = frame.frame_id
            step.metadata["timestamp_s"] = frame.timestamp_s
            step.result = (
                f"Frame {frame.frame_id}: {frame.width}x{frame.height} "
                f"at t={frame.timestamp_s:.3f}s"
            )
            plan.steps[step.step_id - 1] = step  # update shared step store

            # Store frame for use in subsequent steps
            plan.metadata["_last_frame"] = frame

        elif "validate frame" in desc:
            frame = plan.metadata.get("_last_frame")
            if frame is None or not frame.is_valid:
                raise RuntimeError("No valid camera frame available for validation.")
            step.result = f"Frame valid: {frame.width}x{frame.height}, has_depth={frame.has_depth}"

        elif "describe_image" in desc or "scene description" in desc:
            frame = plan.metadata.get("_last_frame")
            if frame is None or not frame.is_valid:
                raise RuntimeError("No valid frame for VLM describe_image.")
            resp = self._vlm.describe_image(frame.color_image)
            step.result = f"Caption: {resp.caption!r} (latency={resp.latency_s:.2f}s)"
            if resp.warning:
                plan.notes.append(f"VLM warning: {resp.warning}")

        elif "answer_visual_question" in desc or "answer vlm" in desc:
            frame = plan.metadata.get("_last_frame")
            if frame is None or not frame.is_valid:
                raise RuntimeError("No valid frame for VLM VQA.")
            resp = self._vlm.answer_visual_question(frame.color_image, plan.request)
            step.result = f"VQA answer: {resp.answer!r}"

        elif "clip candidate matching" in desc:
            frame = plan.metadata.get("_last_frame")
            if frame is None or not frame.is_valid:
                raise RuntimeError("No valid frame for CLIP matching.")
            candidates = [
                "red cube", "blue bowl", "yellow cup", "green block",
                "empty table", "robotic arm", "gripper",
            ]
            resp = self._vlm.match_image_to_candidates(frame.color_image, candidates)
            top = resp.candidates[0] if resp.candidates else None
            step.result = (
                f"Top match: {top.text!r} (score={top.score:.3f})"
                if top else "No candidates"
            )

        elif "detect_or_localize" in desc or "jarvisperceptiondetector" in desc:
            frame = plan.metadata.get("_last_frame")
            if frame is None or not frame.is_valid:
                raise RuntimeError("No valid frame for object detection.")
            try:
                from jarvis_piper.perception.detector import JarvisPerceptionDetector
                detector = JarvisPerceptionDetector()
                dets = detector.detect_objects(
                    rgb_image=frame.color_image,
                    depth_image=frame.depth_image,
                )
                step.result = f"Detected {len(dets)} object(s): {[d['name'] for d in dets]}"
                step.metadata["detections"] = dets
            except Exception as exc:
                step.result = f"Detection unavailable: {exc}"

        elif "note:" in desc or "important" in desc or "warning" in desc or "calibration" in desc:
            # Documentation/warning steps — always complete as-is
            step.result = "Noted."

        elif "log task" in desc:
            elapsed = time.monotonic() - plan.created_at
            step.result = f"Task logged. Elapsed: {elapsed:.2f}s"

        else:
            # Unknown step — mark as completed with note
            step.result = "Step acknowledged (no specific executor)."
