"""
Tests for `jarvis vlm` CLI integration.
"""

import subprocess
import sys


def test_jarvis_vlm_evaluate_cli():
    cmd = [sys.executable, "-m", "jarvis.cli", "vlm", "--evaluate"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    assert result.returncode == 0
    assert "VLM Hardware Evaluation Report" in result.stdout
    assert "System RAM" in result.stdout
    assert "Model Registry" in result.stdout


def test_jarvis_vlm_task_cli():
    cmd = [
        sys.executable,
        "-m",
        "jarvis.cli",
        "vlm",
        "--task",
        "describe the scene",
        "--vlm-type",
        "mock",
        "--cam-type",
        "mock",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    assert result.returncode == 0
    assert "Generated Plan" in result.stdout
    assert "Plan completed: success=True" in result.stdout
