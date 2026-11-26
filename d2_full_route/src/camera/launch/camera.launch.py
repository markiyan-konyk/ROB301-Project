from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([
        # Camera driver
        Node(
            package='v4l2_camera',
            executable='v4l2_camera_node',
            name='v4l2_camera',
            output='screen',
        ),

        # Image processing nodes
        Node(
            package='camera',
            executable='camera_mono',
            name='camera_mono',
            output='screen',
            remappings=[('camera/image', 'image_raw')],
        ),

        Node(
            package='camera',
            executable='camera_rgb',
            name='camera_rgb',
            output='screen',
            remappings=[('camera/image', 'image_raw')],
        ),
    ])
