#!/usr/bin/env python3
"""
JARVIS-PiPER: Live RViz Visualization Launch File.
Launches non-actuating robot_state_publisher and RViz2 for real-time monitoring of:
- PiPER 6-DOF arm & parallel gripper kinematics from CAN bus joint feedback
- RealSense D405 wrist camera images
- Overhead DECXIN camera images
- TF frames and world coordinates

STRICT SAFETY: Purely passive observation. Zero motor commands are transmitted.
"""

import os
from pathlib import Path
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    repo_root = Path(__file__).resolve().parent.parent
    urdf_path = repo_root / "assets" / "piper" / "piper.urdf"
    rviz_config_path = repo_root / "assets" / "rviz" / "live_display.rviz"

    with open(urdf_path, "r", encoding="utf-8") as f:
        robot_description_content = f.read()

    joint_states_topic_arg = DeclareLaunchArgument(
        "joint_states_topic",
        default_value="/piper/joint_states",
        description="Source topic for real-time robot joint feedback"
    )

    robot_state_publisher_node = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        name="robot_state_publisher",
        output="screen",
        parameters=[{
            "robot_description": robot_description_content,
            "publish_frequency": 50.0,
        }],
        remappings=[
            ("joint_states", LaunchConfiguration("joint_states_topic")),
        ]
    )

    rviz_node = Node(
        package="rviz2",
        executable="rviz2",
        name="rviz2",
        output="screen",
        arguments=["-d", str(rviz_config_path)],
    )

    return LaunchDescription([
        joint_states_topic_arg,
        robot_state_publisher_node,
        rviz_node,
    ])
