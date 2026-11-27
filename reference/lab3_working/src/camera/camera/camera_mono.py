#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data

from std_msgs.msg import UInt32
from sensor_msgs.msg import Image
from cv_bridge import CvBridge, CvBridgeError

import numpy as np

# True: black tape on a lighter floor -> the line is the DARKEST column.
# False: white tape on a darker floor -> the line is the BRIGHTEST column.
LINE_IS_DARK = True


class CameraMono(Node):
    def __init__(self):
        super().__init__('camera_mono')

        self.line_idx_pub = self.create_publisher(
            UInt32,
            'line_idx',
            1
        )

        # Sensor-data QoS (best effort) receives images whether the camera
        # driver publishes them reliable or best effort. With the default
        # (reliable) QoS a best-effort camera gives no images and no /line_idx.
        self.camera_subscriber = self.create_subscription(
            Image,
            'camera/image',
            self.camera_callback,
            qos_profile_sensor_data
        )

        self.bridge = CvBridge()
        self.got_first_image = False
        self.get_logger().info('Waiting for camera images...')

    def camera_callback(self, msg):
        try:
            cv_img = self.bridge.imgmsg_to_cv2(msg, 'mono8')
        except CvBridgeError as e:
            self.get_logger().error(str(e))
            return

        if not self.got_first_image:
            self.got_first_image = True
            self.get_logger().info(
                f'Got images ({msg.width}x{msg.height}), publishing /line_idx')

        # Average each column (removing some rows)
        # Result is a 640-length array
        x = np.mean(cv_img[100:300, :], axis=0)

        # Efficient moving window filter
        r = 5
        w = 2 * r + 1

        c = np.cumsum(np.insert(x, 0, 0))
        a = (c[w:] - c[:-w]) / w

        # Add r because we removed r elements from each side
        if LINE_IS_DARK:
            idx = np.argmin(a) + r
        else:
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