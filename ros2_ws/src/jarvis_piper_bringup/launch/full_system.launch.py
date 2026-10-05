#!/usr/bin/env python3
"""
JARVIS-PiPER Unified Master Bringup.
Supports 4 modes via the 'mode' launch argument:
- hardware   : Real PIKA Sense + PiPER arm
- simulation : Gazebo Harmonic physics
- mock       : Zero-dependency synthetic stream generator
- replay     : Passive dataset telemetry playback
"""

import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, OpaqueFunction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration


def launch_setup(context, *args, **kwargs):
    mode = LaunchConfiguration('mode').perform(context)
    bringup_dir = get_package_share_directory('jarvis_piper_bringup')

    if mode == 'hardware':
        launch_file = os.path.join(bringup_dir, 'launch', 'hardware.launch.py')
    elif mode == 'simulation':
        launch_file = os.path.join(bringup_dir, 'launch', 'simulation.launch.py')
    elif mode == 'replay':
        launch_file = os.path.join(bringup_dir, 'launch', 'replay.launch.py')
    else:  # default to mock
        launch_file = os.path.join(bringup_dir, 'launch', 'mock.launch.py')

    return [
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(launch_file),
            launch_arguments=context.launch_configurations.items(),
        )
    ]


def generate_launch_description():
    mode_arg = DeclareLaunchArgument(
        'mode',
        default_value='mock',
        choices=['hardware', 'simulation', 'mock', 'replay'],
        description='Operating mode: hardware, simulation, mock, replay'
    )

    episodes_dir_arg = DeclareLaunchArgument(
        'episodes_dir',
        default_value='dataset/raw',
        description='Directory to store demonstration episodes'
    )

    return LaunchDescription([
        mode_arg,
        episodes_dir_arg,
        OpaqueFunction(function=launch_setup),
    ])
