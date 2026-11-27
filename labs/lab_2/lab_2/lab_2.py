#!/usr/bin/env python3
import math
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import TwistStamped
from std_msgs.msg import UInt32

class Lab02Node(Node):
    def __init__(self):
        super().__init__('lab02')

        # ROS 2 Publisher conversion
        self.cmd_pub = self.create_publisher(TwistStamped, "cmd_vel", 1)

        # ROS 2 Subscriber conversion
        self.color_sub = self.create_subscription(
            UInt32, "line_idx", self.camera_callback, 1
        )
        
        self.get_logger().info('Lab02 node has been initialized.')

    def camera_callback(self, msg):
        """Callback for line index."""
        # access the value using msg.data
        pass

    def follow_the_line(self):
        """
        TODO: complete the function to follow the line
        """
        pass

def main(args=None):
    rclpy.init(args=args)
    node = Lab02Node()  # Fixed class instantiation name
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.destroy_node()

if __name__ == '__main__':
    main()
