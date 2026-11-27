#!/usr/bin/env python3
"""
ROB301 Lab 3: mail delivery.

    ros2 run lab_3 delivery

Follows the line (same PID as lab_2) and stops for 2 s at each address of Table 1,
using the position estimate /state from the localizer. After the last address it
stays stopped. It does not move until both /line_idx and /state are arriving, so
start the localizer first.
"""

import time

from geometry_msgs.msg import TwistStamped
import rclpy
from rclpy.node import Node
from rclpy.signals import SignalHandlerOptions
from std_msgs.msg import Float64, UInt32

# ---- Line following (copy your tuned values from lab_2) -----------------
SPEED = 0.05       # forward speed [m/s] (lab suggests 0.05 to 0.1)
KP = 0.002         # proportional gain [rad/s per pixel]
KI = 0.0           # integral gain
KD = 0.0           # derivative gain
MAX_TURN = 0.5     # largest turn rate sent to the robot [rad/s]
CENTER = 320       # centre column of the image (image is 640 px wide)

# ---- Mail route (Table 1) -----------------------------------------------
ADDRESSES = [0.61, 1.22, 2.44, 3.05]   # [m] along the line from O
STOP_TIME = 2.0                         # [s] stop at each address
# -------------------------------------------------------------------------


class Delivery(Node):

    def __init__(self):
        super().__init__('delivery')

        self.cmd_pub = self.create_publisher(TwistStamped, 'cmd_vel', 1)
        self.create_subscription(UInt32, 'line_idx', self.camera_callback, 1)
        self.create_subscription(Float64, 'state', self.state_callback, 1)

        self.line_idx = None    # None until the camera works
        self.x = None           # None until the localizer runs
        self.integral = 0.0
        self.last_error = 0.0

        self.next_stop = 0      # index of the next address in ADDRESSES
        self.stop_until = None  # end time of the current stop [s], None = driving

        self.get_logger().info('Waiting for /line_idx and /state ...')

    # Steer once per new camera frame (never on an old reading)
    def camera_callback(self, msg):
        self.line_idx = msg.data
        self.control_loop()

    def state_callback(self, msg):
        self.x = msg.data

    def control_loop(self):
        if self.line_idx is None or self.x is None:
            return    # wait for the camera and the localizer

        now = time.time()

        # Stopped at an address: wait, then go on to the next one
        if self.stop_until is not None:
            if now < self.stop_until:
                self.drive(0.0, 0.0)
                return
            self.stop_until = None
            self.next_stop += 1

        # Route finished: stay stopped
        if self.next_stop >= len(ADDRESSES):
            self.drive(0.0, 0.0)
            return

        # Reached the next address: start a stop
        if self.x >= ADDRESSES[self.next_stop]:
            self.get_logger().info(
                f'Address {self.next_stop + 1} ({ADDRESSES[self.next_stop]:.2f} m): '
                f'stopping at estimate x = {self.x:.3f} m. Measure the real position now.')
            self.stop_until = now + STOP_TIME
            self.drive(0.0, 0.0)
            return

        # Otherwise follow the line (PID, same as lab_2)
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
    node = Delivery()
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
