#!/usr/bin/env python3

"""
Publish the bearing of the CN Tower on /scan_angle [rad], measured counter-clockwise
from the robot's heading (straight ahead = 0, straight to the left = pi/2).

    ros2 run lab_3 scan_angle_publisher      (or: ros2 launch lab_3 lab3.launch.py)

Calibration (Section 4.3): place the robot so the tower is at a known bearing (e.g.
exactly to its left, 90 deg), read the "raw" angle this node prints, then set
ANGLE_OFFSET_DEG = known - raw.
"""

import math

import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import LaserScan
from std_msgs.msg import Float64

ANGLE_OFFSET_DEG = 0.0   # lidar calibration: known angle - raw angle [deg]

# Anything inside this window on the robot's LEFT counts as the tower
Y_MIN, Y_MAX = 0.50, 0.65   # sideways distance from the robot [m]
R_MIN, R_MAX = 0.10, 2.0    # range [m]


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
        ranges = np.array(msg.ranges)
        ranges[~np.isfinite(ranges)] = 0.0   # inf / nan = no return

        # Angle of every reading, taken from the scan itself
        angles = msg.angle_min + np.arange(len(ranges)) * msg.angle_increment

        # Sideways (y) distance of every reading; y > 0 is the robot's left
        y_range = ranges * np.sin(angles)

        tower = ((Y_MIN <= y_range) & (y_range <= Y_MAX)
                 & (R_MIN <= ranges) & (ranges <= R_MAX))

        # Tower not visible (hidden or out of range): publish nothing
        if not np.any(tower):
            return

        # Several readings hit the tower: take the median angle
        raw = float(np.median(angles[tower]))
        angle = raw + math.radians(ANGLE_OFFSET_DEG)

        angle_msg = Float64()
        angle_msg.data = angle
        self.angle_pub.publish(angle_msg)

        self.get_logger().info(
            f'raw {math.degrees(raw):6.1f} deg   '
            f'published {math.degrees(angle):6.1f} deg',
            throttle_duration_sec=1.0)


def main(args=None):
    rclpy.init(args=args)

    pub = ScanAnglePublisher()

    try:
        rclpy.spin(pub)
    except KeyboardInterrupt:
        pass

    pub.destroy_node()
    rclpy.try_shutdown()


if __name__ == '__main__':
    main()
