#!/usr/bin/env python3

import rclpy
from rclpy.node import Node

from std_msgs.msg import UInt32
from sensor_msgs.msg import Image
from cv_bridge import CvBridge, CvBridgeError

import numpy as np


class CameraMono(Node):
    def __init__(self):
        super().__init__('camera_mono')

        self.line_idx_pub = self.create_publisher(
            UInt32,
            'line_idx',
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
            cv_img = self.bridge.imgmsg_to_cv2(msg, 'mono8')
        except CvBridgeError as e:
            self.get_logger().error(str(e))
            return

        # Average each column (removing some rows)
        # Result is a 640-length array
        x = np.mean(cv_img[100:300, :], axis=0)

        # Efficient moving window filter
        r = 5
        w = 2 * r + 1

        c = np.cumsum(np.insert(x, 0, 0))
        a = (c[w:] - c[:-w]) / w

        # Add r because we removed r elements from each side
        idx = np.argmax(a) + r

        msg = UInt32()
        msg.data = int(idx)

        self.line_idx_pub.publish(msg)


def main(args=None):
    rclpy.init(args=args)

    camera = CameraMono()

    rclpy.spin(camera)

    camera.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()