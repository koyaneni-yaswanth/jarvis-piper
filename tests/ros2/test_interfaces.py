"""
Tests for ROS 2 interface messages and services definitions.
"""

from pathlib import Path


def test_interface_files_exist():
    repo_root = Path(__file__).resolve().parent.parent.parent
    msg_dir = repo_root / "ros2_ws" / "src" / "jarvis_piper_interfaces" / "msg"
    srv_dir = repo_root / "ros2_ws" / "src" / "jarvis_piper_interfaces" / "srv"

    assert msg_dir.exists()
    assert (msg_dir / "SynchronizedFrame.msg").exists()
    assert (msg_dir / "EpisodeMetadata.msg").exists()
    assert (msg_dir / "RecorderStatus.msg").exists()

    assert srv_dir.exists()
    assert (srv_dir / "StartEpisode.srv").exists()
    assert (srv_dir / "StopEpisode.srv").exists()
    assert (srv_dir / "ExportDataset.srv").exists()
