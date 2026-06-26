#!/usr/bin/env python3

"""
This script defines a ROS2 node that integrates with Ollama's language model to control a TurtleBot3 robot.
The node subscribes to a topic and processes incoming messages using an AI agent with predefined tools for navigation and pose retrieval.

Classes:
    ROS2AIAgent(Node): A ROS2 node that subscribes to a topic and uses an AI agent to process messages and control the robot.

Functions:
    move_to_goal(x: float, y: float) -> str: Navigates the robot to specified x, y coordinates.
    get_current_pose() -> str: Retrieves the current position and orientation of the robot.
    pose_callback(msg: Odometry): Callback function to update the robot's pose.
    prompt_callback(msg: String): Callback function to process incoming messages.
    main(args=None): Initializes and spins the ROS2 node.

Dependencies:
    - math
    - geometry_msgs.msg (PoseStamped)
    - nav_msgs.msg (Odometry)
    - rclpy.action (ActionClient)
    - nav2_msgs.action (NavigateToPose)
    - std_msgs.msg (String)
    - rclpy (rclpy, Node)
    - ament_index_python.packages (get_package_share_directory)
    - pathlib (Path)
    - transforms3d.euler (quat2euler)
    - Ollama integration: langchain_ollama, langchain
    - langchain.tools (tool)
"""

import math
from pathlib import Path

import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from std_msgs.msg import String
from geometry_msgs.msg import PoseStamped
from nav_msgs.msg import Odometry
from nav2_msgs.action import NavigateToPose
from ament_index_python.packages import get_package_share_directory

from transforms3d.euler import quat2euler
from langchain_ollama import ChatOllama
from langchain.agents import create_agent
from langchain.tools import tool


class ROS2AIAgent(Node):
    def __init__(self):
        super().__init__('ros2_ai_agent')
        self.get_logger().info('ROS2 AI Agent has been started')
        
        # Initialize robot pose
        self.current_pose = PoseStamped()
        
        # Create action client for navigation
        self.nav_client = ActionClient(self, NavigateToPose, 'navigate_to_pose')
        
        # Create subscriber for robot pose
        self.pose_sub = self.create_subscription(
            Odometry,
            '/odom',
            self.pose_callback,
            10
        )

        # Create tools using class methods
        self.move_to_goal_tool = tool(self.move_to_goal)
        self.get_current_pose_tool = tool(self.get_current_pose)

        system_prompt = """You are a TurtleBot3 control assistant.
        You can control the robot using these commands:
        - move_to_goal(x, y): Navigate robot to specified x,y coordinates
        - get_current_pose(): Get current position and orientation of robot
        
        Return only the necessary actions and their results. e.g
        Human: Move the robot to position x=1.0, y=2.0
        AI: Navigating to position x: 1.0, y: 2.0"""

        #share_dir = get_package_share_directory('ros2_agent')
        #config_dir = share_dir + '/config' + '/openai.env'
        #load_dotenv(Path(config_dir))

        # setup the toolkit with the decorated class methods
        self.toolkit = [self.move_to_goal_tool, self.get_current_pose_tool]

        # Choose the LLM that will drive the agent
        self.llm = ChatOllama(model="qwen3:8b", temperature=0)

        # Construct the unified, modern tool-calling agent runner directly
        # In the modern interface, create_agent returns a self-contained runtime graph
        self.agent_executor = create_agent(self.llm, tools=self.toolkit, system_prompt=system_prompt)

        # Create the subscriber for prompts
        self.subscription = self.create_subscription(
            String,
            'prompt',
            self.prompt_callback,
            10
        )

    def move_to_goal(self, x: float, y: float) -> str:
        """Navigate robot to specified x,y coordinates."""
        goal_msg = NavigateToPose.Goal()
        goal_msg.pose.header.frame_id = 'map'
        goal_msg.pose.header.stamp = self.get_clock().now().to_msg()
        goal_msg.pose.pose.position.x = float(x)
        goal_msg.pose.pose.position.y = float(y)
        goal_msg.pose.pose.orientation.w = 1.0
        
        # Wait for action server
        if not self.nav_client.wait_for_server(timeout_sec=5.0):
            return "Navigation server not available"
        
        # Send goal
        self.nav_client.send_goal_async(goal_msg)
        return f"Navigating to position x: {x}, y: {y}"

    def get_current_pose(self) -> str:
        """Get current pose of the robot."""
        x = self.current_pose.pose.position.x
        y = self.current_pose.pose.position.y
        orientation = self.current_pose.pose.orientation
        roll, pitch, yaw = quat2euler([
            orientation.w,
            orientation.x,
            orientation.y,
            orientation.z
        ])
        return f"x: {x:.2f}, y: {y:.2f}, theta: {math.degrees(yaw):.2f} degrees"

    def pose_callback(self, msg):
        """Callback to update robot's pose"""
        self.current_pose.pose = msg.pose.pose
        self.current_pose.header = msg.header

    def prompt_callback(self, msg):
        try:
            self.get_logger().info(f"Received prompt: {msg.data}")
            # The modern engine expects standard messages structure
            result = self.agent_executor.invoke({
                "messages": [{"role": "user", "content": msg.data}]
            })
            # Grab the final output content block from the message layout
            final_response = result["messages"][-1].content
            self.get_logger().info(f"Result: {final_response}")
        except Exception as e:
            self.get_logger().error(f'Error processing prompt: {str(e)}')


def main(args=None):
    rclpy.init(args=args)
    node = ROS2AIAgent()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()


if __name__ == '__main__':
    main()
