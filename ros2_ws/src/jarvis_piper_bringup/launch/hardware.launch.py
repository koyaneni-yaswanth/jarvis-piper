#!/usr/bin/env python3
"""
Hardware Mode Launch File.
Launches synchronization and recording nodes connected to real PIKA Sense and PiPER arm topics.
"""

from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration


def generate_launch_description():
    can_interface_arg = DeclareLaunchArgument(
        'can_interface',
        default_value='can0',
        description='CAN interface name for PiPER arm'
    )

    episodes_dir_arg = DeclareLaunchArgument(
        'episodes_dir',
        default_value='dataset/raw',
        description='Directory to store demonstration episodes'
    )

    sync_node = Node(
        package='jarvis_piper_sync',
        executable='time_synchronizer_node',
        name='time_synchronizer_node',
        output='screen',
        parameters=[{
            'target_hz': 50.0,
            'max_slop_sec': 0.03,
            'piper_joint_topic': '/piper/joint_states',
            'pika_pose_topic': '/pika_pose',
            'camera_topic': '/camera',
            'depth_topic': '/camera/depth_image',
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
        can_interface_arg,
        episodes_dir_arg,
        sync_node,
        recorder_node,
    ])
