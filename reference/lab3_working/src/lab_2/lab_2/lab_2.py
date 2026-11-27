#!/usr/bin/env python3
"""
ROB301 Lab 2: line following with a PID controller.

    ros2 run lab_2 lab_2

Reads /line_idx (column of the line in the 640 px wide camera image, published by
the camera package on the TurtleBot) and publishes /cmd_vel.

    P controller:   KI = 0, KD = 0
    PI controller:  KD = 0
    PID controller: all three
"""

import time

from geometry_msgs.msg import TwistStamped
import rclpy
from rclpy.node import Node
from rclpy.signals import SignalHandlerOptions
from std_msgs.msg import UInt32

# ---- Tuning -------------------------------------------------------------
SPEED = 0.05       # forward speed [m/s]
KP = 0.002         # proportional gain [rad/s per pixel]
KI = 0.0           # integral gain
KD = 0.0           # derivative gain
MAX_TURN = 0.5     # largest turn rate sent to the robot [rad/s]
CENTER = 320       # centre column of the image (image is 640 px wide)
# -------------------------------------------------------------------------


class Lab02Node(Node):

    def __init__(self):
        super().__init__('lab_2')

        self.cmd_pub = self.create_publisher(TwistStamped, 'cmd_vel', 1)
        self.create_subscription(UInt32, 'line_idx', self.camera_callback, 1)

        self.line_idx = None
        self.integral = 0.0
        self.last_error = 0.0

        self.get_logger().info('Waiting for /line_idx ...')

    # Steer once per new camera frame (never on an old reading)
    def camera_callback(self, msg):
        self.line_idx = msg.data
        self.follow_the_line()

    def follow_the_line(self):
        # error > 0: the line is left of centre, so turn left (positive turn rate)
        error = CENTER - self.line_idx
        self.integral += error
        derivative = error - self.last_error
        self.last_error = error

        turn = KP * error + KI * self.integral + KD * derivative
        turn = max(-MAX_TURN, min(MAX_TURN, turn))
        self.drive(SPEED, turn)

    def drive(self, speed, turn):
        msg = TwistStamped()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.twist.linear.x = float(speed)
        msg.twist.angular.z = float(turn)
        self.cmd_pub.publish(msg)


def main(args=None):
    # Ctrl+C is handled here (not by rclpy) so we can still send a stop command
    rclpy.init(args=args, signal_handler_options=SignalHandlerOptions.NO)
    node = Lab02Node()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        for _ in range(3):
            node.drive(0.0, 0.0)   # stop the robot
            time.sleep(0.05)
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
