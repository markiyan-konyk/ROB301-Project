#!/usr/bin/env python3

import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import LaserScan
from std_msgs.msg import Float64


class ScanAnglePublisher(Node):

    def __init__(self):
        super().__init__('scan_angle_publisher')

        # Sensor-data QoS (best effort) receives /scan whether the lidar driver
        # publishes it reliable or best effort
        self.scan_sub = self.create_subscription(
            LaserScan,
            'scan',
            self.scan_cb,
            qos_profile_sensor_data
        )

        self.angle_pub = self.create_publisher(
            Float64,
            'scan_angle',
            1
        )

    def scan_cb(self, msg):
        # Only use the scan where y >= 0
        # (i.e. to the left side of the robot)
        in_range = np.array(msg.ranges[0:180])
        angles = np.deg2rad(np.arange(0, 180))

        # Compute the y-distance to each measurement
        y_range = in_range * np.sin(angles)

        # Filter measurements:
        # range in [0.1, 2] m
        # y_range in [0.5, 0.65] m
        angles = angles[
            (0.5 <= y_range)
            & (y_range <= 0.65)
            & (0.1 <= in_range)
            & (in_range <= 2)
        ]

        # If no valid measurements, don't publish anything
        if len(angles) == 0:
            return

        # If multiple measurements, take the median
        angle = np.median(angles)

        # Publish the angle
        angle_msg = Float64()
        angle_msg.data = float(angle)

        self.angle_pub.publish(angle_msg)


def main(args=None):
    rclpy.init(args=args)

    pub = ScanAnglePublisher()

    rclpy.spin(pub)

    pub.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
