#!/usr/bin/env python3
"""
Monitor Mode Launch File.
Launches live web dashboard and terminal dashboard nodes.
"""

from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration


def generate_launch_description():
    port_arg = DeclareLaunchArgument(
        'port',
        default_value='8080',
        description='Port for web operator dashboard'
    )

    web_dashboard_node = Node(
        package='jarvis_piper_monitor',
        executable='web_dashboard_node',
        name='web_dashboard_node',
        output='screen',
        parameters=[{
            'port': LaunchConfiguration('port'),
        }]
    )

    terminal_dashboard_node = Node(
        package='jarvis_piper_monitor',
        executable='terminal_dashboard',
        name='terminal_dashboard',
        output='screen',
    )

    return LaunchDescription([
        port_arg,
        web_dashboard_node,
        terminal_dashboard_node,
    ])
