#!/usr/bin/env python3
"""
Mock Mode Launch File.
Starts zero-dependency synthetic hardware streamer, time synchronizer, and episode recorder.
"""

from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration


def generate_launch_description():
    episodes_dir_arg = DeclareLaunchArgument(
        'episodes_dir',
        default_value='dataset/raw',
        description='Path to store recorded demonstration episodes'
    )

    publish_rate_arg = DeclareLaunchArgument(
        'publish_rate',
        default_value='50.0',
        description='Simulation telemetry rate in Hz'
    )

    mock_streamer_node = Node(
        package='jarvis_piper_tools',
        executable='pika_piper_mock_streamer',
        name='mock_streamer_node',
        output='screen',
        parameters=[{
            'rate_hz': LaunchConfiguration('publish_rate'),
            'publish_camera': True,
        }]
    )

    sync_node = Node(
        package='jarvis_piper_sync',
        executable='time_synchronizer_node',
        name='time_synchronizer_node',
        output='screen',
        parameters=[{
            'target_hz': 50.0,
            'max_slop_sec': 0.04,
        }]
    )

    recorder_node = Node(
        package='jarvis_piper_recorder',
        executable='recorder_node',
        name='recorder_node',
        output='screen',
        parameters=[{
            'episodes_dir': LaunchConfiguration('episodes_dir'),
            'auto_record': False,
        }]
    )

    return LaunchDescription([
        episodes_dir_arg,
        publish_rate_arg,
        mock_streamer_node,
        sync_node,
        recorder_node,
    ])
