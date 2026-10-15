"""
Tests for Vision-Language Task Planner and Safety Gating.
"""

import pytest
from jarvis_piper.tasks.vlm_planner import (
    VisionTaskPlanner,
    TaskPlan,
    PlanStep,
    StepStatus,
    TaskType,
    classify_task,
)
from jarvis_piper.perception.vlm_mock import MockVLMAdapter
from jarvis_piper.perception.camera import MockCamera


def test_classify_task():
    assert classify_task("describe what you see on the table") == TaskType.SCENE_DESCRIPTION
    assert classify_task("is there a blue cup?") == TaskType.VISUAL_QUERY
    assert classify_task("what color is the block?") == TaskType.OBJECT_IDENTIFICATION
    assert classify_task("where is the red block located?") == TaskType.OBJECT_LOCALIZATION
    assert classify_task("pick up the red block and place it in the bowl") == TaskType.MANIPULATION
    assert classify_task("xyz random sentence") == TaskType.UNKNOWN


def test_plan_scene_description():
    vlm = MockVLMAdapter(fixed_caption="a robotic table with a cube")
    cam = MockCamera()
    planner = VisionTaskPlanner(vlm=vlm, camera=cam)

    plan = planner.plan("describe the scene")
    assert isinstance(plan, TaskPlan)
    assert len(plan.steps) == 5
    assert not plan.is_hardware_task

    # Execute plan safely
    executed = planner.execute_plan(plan)
    assert executed.success is True
    assert all(s.status == StepStatus.COMPLETED for s in executed.steps)
    assert "a robotic table with a cube" in executed.steps[2].result


def test_plan_manipulation_hardware_gating():
    vlm = MockVLMAdapter()
    cam = MockCamera()
    planner = VisionTaskPlanner(vlm=vlm, camera=cam)

    plan = planner.plan("pick up the red cube and place it into the bin")
    assert plan.is_hardware_task

    # When executed WITHOUT operator authorization, hardware steps MUST be blocked
    executed = planner.execute_plan(plan, operator_authorized=False)
    assert executed.success is False

    awaiting_steps = [s for s in executed.steps if s.status == StepStatus.AWAITING_OPERATOR]
    assert len(awaiting_steps) > 0
    for s in awaiting_steps:
        assert "operator authorization required" in s.result.lower()
