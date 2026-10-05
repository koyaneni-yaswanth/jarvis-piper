#!/usr/bin/env python3
"""
Replay Mode Launch File.
Launches passive dataset playback node and visualization monitor.
"""

from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration


def generate_launch_description():
    episode_path_arg = DeclareLaunchArgument(
        'episode_path',
        default_value='dataset/raw',
        description='Path to episode directory or raw dataset'
    )

    playback_rate_arg = DeclareLaunchArgument(
        'playback_rate',
        default_value='50.0',
        description='Playback frequency in Hz'
    )

    loop_arg = DeclareLaunchArgument(
        'loop',
        default_value='false',
        description='Loop playback indefinitely'
    )

    replay_node = Node(
        package='jarvis_piper_replay',
        executable='replay_node',
        name='replay_node',
        output='screen',
        parameters=[{
            'episode_path': LaunchConfiguration('episode_path'),
            'playback_rate': LaunchConfiguration('playback_rate'),
            'loop': LaunchConfiguration('loop'),
        }]
    )

    return LaunchDescription([
        episode_path_arg,
        playback_rate_arg,
        loop_arg,
        replay_node,
    ])
