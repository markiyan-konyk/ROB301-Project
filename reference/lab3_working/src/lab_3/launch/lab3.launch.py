"""
Lab 3 helper nodes: the CN Tower bearing (/scan_angle) and the noisy speed (/cmd_vel_noisy).

    ros2 launch lab_3 lab3.launch.py

Run it on the Remote PC. The camera runs only on the TurtleBot (camera.launch.py).
"""

from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([
        Node(
            package='lab_3',
            executable='scan_angle_publisher',
            name='scan_angle_publisher',
            output='screen',
        ),

        Node(
            package='lab_3',
            executable='noisy_vel_publisher',
            name='noisy_vel_publisher',
            output='screen',
        ),
    ])
