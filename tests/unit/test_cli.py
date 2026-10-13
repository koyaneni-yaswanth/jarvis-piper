"""
Unit tests for JARVIS-PiPER CLI command execution.
"""

import sys
import pytest
from jarvis_piper.cli.main import main


def test_cli_version(capsys):
    sys.argv = ["jarvis-piper", "version"]
    res = main()
    assert res == 0
    captured = capsys.readouterr()
    assert "1.0.0" in captured.out


def test_cli_doctor(capsys):
    sys.argv = ["jarvis-piper", "doctor"]
    res = main()
    assert res == 0
    captured = capsys.readouterr()
    assert "SYSTEM & HARDWARE CHECK" in captured.out


def test_cli_demo(tmp_path, capsys):
    out_dir = tmp_path / "mock_demo"
    sys.argv = ["jarvis-piper", "demo", "--episodes", "1", "--steps", "10", "--output-dir", str(out_dir)]
    res = main()
    assert res == 0
    assert out_dir.exists()
    subdirs = list(out_dir.iterdir())
    assert len(subdirs) == 1
    assert (subdirs[0] / "metadata.json").exists()
    assert (subdirs[0] / "trajectory.json").exists()


def test_cli_demo_themes(tmp_path, capsys):
    out_dir = tmp_path / "curriculum_demo"
    sys.argv = ["jarvis-piper", "demo", "--theme", "all", "--episodes", "1", "--steps", "10", "--output-dir", str(out_dir)]
    res = main()
    assert res == 0
    subdirs = list(out_dir.iterdir())
    assert len(subdirs) == 3

