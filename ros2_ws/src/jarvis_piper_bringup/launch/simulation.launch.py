#!/usr/bin/env python3
"""
Simulation Mode Launch File.
Launches Gazebo/Simulated robot drivers, synchronizer, and recording pipeline.
"""

from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration


def generate_launch_description():
    episodes_dir_arg = DeclareLaunchArgument(
        'episodes_dir',
        default_value='dataset/raw',
        description='Directory to store demonstration episodes'
    )

    use_sim_time_arg = DeclareLaunchArgument(
        'use_sim_time',
        default_value='true',
        description='Use simulation clock'
    )

    sync_node = Node(
        package='jarvis_piper_sync',
        executable='time_synchronizer_node',
        name='time_synchronizer_node',
        output='screen',
        parameters=[{
            'use_sim_time': LaunchConfiguration('use_sim_time'),
            'target_hz': 50.0,
            'max_slop_sec': 0.05,
        }]
    )

    recorder_node = Node(
        package='jarvis_piper_recorder',
        executable='recorder_node',
        name='recorder_node',
        output='screen',
        parameters=[{
            'use_sim_time': LaunchConfiguration('use_sim_time'),
            'episodes_dir': LaunchConfiguration('episodes_dir'),
            'auto_record': False,
        }]
    )

    return LaunchDescription([
        episodes_dir_arg,
        use_sim_time_arg,
        sync_node,
        recorder_node,
    ])
