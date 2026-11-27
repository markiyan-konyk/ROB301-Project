import math

import rclpy
from rclpy.node import Node
from nav_msgs.msg import Odometry
from rclpy.qos import qos_profile_sensor_data


def get_yaw_from_quaternion(q):
    siny_cosp = 2 * (q.w * q.z + q.x * q.y)
    cosy_cosp = 1 - 2 * (q.y * q.y + q.z * q.z)
    yaw = math.atan2(siny_cosp, cosy_cosp)
    return yaw


class OdometryNode(Node):
    def __init__(self):
        super().__init__("odometry_node")

        odom_topic = "odom"

        self.subscription = self.create_subscription(
            Odometry,
            odom_topic,
            self.callback,
            qos_profile_sensor_data,
        )

        self.get_logger().info(f"odometry_node started: subscribing to '{odom_topic}'")

    def callback(self, odom_data: Odometry):
        x = odom_data.pose.pose.position.x
        y = odom_data.pose.pose.position.y
        
        orientation = odom_data.pose.pose.orientation
        yaw = get_yaw_from_quaternion(orientation)
        yaw_deg = math.degrees(yaw)


        self.get_logger().info(f"x: {x:.2f}, y: {y:.2f}, yaw: {yaw_deg:.2f}")


def main(args=None):
    rclpy.init(args=args)
    node = OdometryNode()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
