#!/usr/bin/env python3

"""Add Gaussian noise to /cmd_vel and republish it on /cmd_vel_noisy."""

from geometry_msgs.msg import TwistStamped
import numpy as np
import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node


class NoiseMaker(Node):

    def __init__(self, mu=0.0, std=1e-5):
        super().__init__('noisy_vel_publisher')

        self.mu = mu
        self.std = std

        self.cmd_sub = self.create_subscription(
            TwistStamped,
            'cmd_vel',
            self.cmd_callback,
            10
        )

        self.cmd_pub = self.create_publisher(
            TwistStamped,
            'cmd_vel_noisy',
            1
        )

        self.get_logger().info(
            f'Adding N({self.mu}, {self.std}^2) m/s noise to cmd_vel.linear.x')

    def cmd_callback(self, msg):
        # Create a new message rather than modifying the received one.
        # TwistStamped wraps the velocities in a .twist field.
        noisy = TwistStamped()
        noisy.header = msg.header

        noisy.twist.linear.x = (
            msg.twist.linear.x
            + np.random.normal(loc=self.mu, scale=self.std)
        )

        # Copy the remaining fields unchanged
        noisy.twist.linear.y = msg.twist.linear.y
        noisy.twist.linear.z = msg.twist.linear.z

        noisy.twist.angular.x = msg.twist.angular.x
        noisy.twist.angular.y = msg.twist.angular.y
        noisy.twist.angular.z = msg.twist.angular.z

        self.cmd_pub.publish(noisy)


def main(args=None):
    rclpy.init(args=args)

    mu_noise = 0.0
    std_noise = 0.01

    noise_maker = NoiseMaker(
        mu=mu_noise,
        std=std_noise
    )

    try:
        rclpy.spin(noise_maker)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass

    noise_maker.destroy_node()
    rclpy.try_shutdown()


if __name__ == '__main__':
    main()
