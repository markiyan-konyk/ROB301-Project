#!/usr/bin/env python3
import rclpy
from rclpy.node import Node

class FinalProject(Node):
    def __init__(self):
        super().__init__('Final_Project')
        self.get_logger().info('Final Project node has been initialized.')


def main():
    rclpy.init()
    node = FinalProject()
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.destroy_node()

if __name__ == '__main__':
    main()
