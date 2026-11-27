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

        # camera_rgb (mean colour, /mean_img_rgb) is not used in Labs 2-3 and
        # slows the Pi down, so it is not started here.
    ])
