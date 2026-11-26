#!/usr/bin/env python3

"""Get mean color (r, g, b) value and publish to /mean_img_rgb"""

import rclpy
from rclpy.node import Node

from std_msgs.msg import Float64MultiArray
from sensor_msgs.msg import Image
from cv_bridge import CvBridge, CvBridgeError

import numpy as np


class CameraRGB(Node):
    def __init__(self):
        super().__init__('camera_rgb')

        self.color_sensor_publisher = self.create_publisher(
            Float64MultiArray,
            'mean_img_rgb',
            1
        )

        self.camera_subscriber = self.create_subscription(
            Image,
            'camera/image',
            self.camera_callback,
            1
        )

        self.bridge = CvBridge()

    def camera_callback(self, msg):
        try:
            rgb_cv_img = self.bridge.imgmsg_to_cv2(msg, 'rgb8')
        except CvBridgeError as e:
            self.get_logger().error(str(e))
            return

        # Get mean RGB value of the top 200 rows
        color = np.mean(rgb_cv_img[:200], axis=(0, 1))

        # Publish the color sensor reading
        color_msg = Float64MultiArray()
        color_msg.data = color.tolist()

        self.color_sensor_publisher.publish(color_msg)


def main(args=None):
    rclpy.init(args=args)

    camera = CameraRGB()

    rclpy.spin(camera)

    camera.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()