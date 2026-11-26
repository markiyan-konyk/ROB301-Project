"""D2: drive one loop, counting patch arrivals without localization."""
import argparse
import time

import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from rclpy.signals import SignalHandlerOptions
from rclpy.utilities import remove_ros_args
from geometry_msgs.msg import TwistStamped
from std_msgs.msg import Float64MultiArray, UInt32

from .logic import PID, Route, classify, load_colors, sensors_fresh, valid_rgb

# ---- Tunable constants (Remote PC) ----
SPEED = 0.05
KP = 0.002
KI = 0.0
KD = 0.0
MAX_TURN = 0.5
CENTER = 320
DEBOUNCE = 3
NUM_OFFICES = 11
MAP = ['yellow', 'green', 'blue', 'orange', 'orange', 'green', 'blue', 'orange', 'yellow', 'green', 'blue']
CONTROL_HZ = 20.0
STALE_SECONDS = 1.0
WARNING_INTERVAL = 2.0
# MAP documents driving order; D2 does not infer office identities.


class RouteFollower(Node):
    def __init__(self, offices):
        super().__init__('route_follower')
        self.route = Route(offices, DEBOUNCE)
        self.pid = PID(KP, KI, KD, MAX_TURN)
        self.means, warning = load_colors()
        if warning:
            self.get_logger().warning(warning)
        self.line_time = self.rgb_time = None
        self.line_idx = CENTER
        self.last_tick = time.monotonic()
        self.last_warning = float('-inf')
        self.pub = self.create_publisher(TwistStamped, '/cmd_vel', 10)
        self.create_subscription(UInt32, '/line_idx', self.on_line, qos_profile_sensor_data)
        self.create_subscription(Float64MultiArray, '/mean_img_rgb', self.on_rgb, qos_profile_sensor_data)
        self.create_timer(1/CONTROL_HZ, self.control)
        self.get_logger().info(f'Start ON_PATCH; stopping after {offices} arrivals. Waiting for both camera topics.')

    def on_line(self, msg):
        if 0 <= msg.data <= 639:
            self.line_idx = msg.data
            self.line_time = time.monotonic()

    def on_rgb(self, msg):
        if not valid_rgb(msg.data):
            return
        now = time.monotonic()
        if not sensors_fresh(now, self.line_time, self.rgb_time, STALE_SECONDS):
            self.route.reset_pending()
        self.rgb_time = now
        if not sensors_fresh(now, self.line_time, self.rgb_time, STALE_SECONDS):
            return
        old_state = self.route.state
        reached = self.route.observe(classify(msg.data, self.means))
        if old_state != self.route.state:
            self.pid.reset()
        if reached:
            self.get_logger().info(f'Office #{self.route.count} reached: {reached}')
            if self.route.state == 'DONE':
                self.publish_velocity()
                self.get_logger().info('Full route done')

    def publish_velocity(self, speed=0.0, turn=0.0):
        msg = TwistStamped()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.twist.linear.x = float(speed)
        msg.twist.angular.z = float(turn)
        self.pub.publish(msg)

    def control(self):
        now = time.monotonic()
        dt = max(now-self.last_tick, 1e-6)
        self.last_tick = now
        if self.route.state == 'DONE':
            self.publish_velocity()
            return
        if not sensors_fresh(now, self.line_time, self.rgb_time, STALE_SECONDS):
            self.publish_velocity()
            self.pid.reset()
            self.route.reset_pending()
            if now-self.last_warning >= WARNING_INTERVAL:
                self.get_logger().warning('STOPPED: waiting for fresh /line_idx AND /mean_img_rgb (<= 1 s).')
                self.last_warning = now
            return
        turn = self.pid.update(CENTER-self.line_idx, dt) if self.route.state == 'FOLLOW_LINE' else 0.0
        self.publish_velocity(SPEED, turn)

    def stop(self):
        for _ in range(5):
            self.publish_velocity()
            time.sleep(0.05)


def main(args=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('N', nargs='?', type=int, default=NUM_OFFICES)
    options = parser.parse_args(remove_ros_args(args=args)[1:])
    if options.N < 1:
        parser.error('N must be a positive integer')
    rclpy.init(args=args, signal_handler_options=SignalHandlerOptions.NO)
    node = None
    try:
        node = RouteFollower(options.N)
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        if node is not None:
            try:
                node.stop()
            finally:
                node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
