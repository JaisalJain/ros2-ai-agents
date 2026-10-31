#!/usr/bin/env python3

"""
This script defines a ROS2 node that integrates with Ollama's language model to control a turtle in the turtlesim simulation.
The node subscribes to a topic and processes incoming messages using an AI agent with predefined tools.

Classes:
    ROS2AIAgent(Node): A ROS2 node that subscribes to a topic and uses an AI agent to control the turtle.

Functions:
    move_forward(distance: float) -> str: Moves the turtle forward by the specified distance.
    rotate(angle: float) -> str: Rotates the turtle by the specified angle in degrees.
    get_pose() -> str: Gets the current position and orientation of the turtle.
    publish_motion(msg: Twist): Publishes a velocity command and waits until turtlesim has finished it.
    pose_callback(msg: Pose): Callback function to update the turtle's pose.
    prompt_callback(msg: String): Callback function to process incoming messages.
    main(args=None): Initializes and spins the ROS2 node.

Dependencies:
    - math, threading, time
    - geometry_msgs.msg (Twist)
    - turtlesim.msg (Pose)
    - std_msgs.msg (String)
    - rclpy (Node)
    - Ollama integration: langchain_ollama, langchain
    - langchain.tools (tool)
    - ros2_agent.node_runner (prompt_worker, run_node)
"""

import math
import threading
import time

from rclpy.node import Node
from std_msgs.msg import String
from geometry_msgs.msg import Twist
from turtlesim.msg import Pose

from langchain_ollama import ChatOllama
from langchain.agents import create_agent
from langchain.tools import tool

from ros2_agent.node_runner import prompt_worker, run_node

# turtlesim applies each velocity command for 1 second and then stops the turtle.
COMMAND_DURATION = 1.0


class ROS2AIAgent(Node):
    def __init__(self):
        super().__init__('ros2_ai_agent')
        self.get_logger().info('ROS2 AI Agent has been started')
        
        # Initialize turtle pose
        self.turtle_pose = Pose()

        # Run one motion command at a time, so tool calls made in the same step
        # don't overwrite each other
        self.motion_lock = threading.Lock()
        
        # Create publisher for turtle commands
        self.cmd_vel_pub = self.create_publisher(Twist, '/turtle1/cmd_vel', 10)
        
        # Create subscriber for turtle pose
        self.pose_sub = self.create_subscription(
            Pose,
            '/turtle1/pose',
            self.pose_callback,
            10
        )

        # setup the tools as class methods
        @tool
        def move_forward(distance: float) -> str:
            """Move turtle forward by specified distance (negative moves backward)."""
            msg = Twist()
            # The command lasts 1 second, so a speed equal to the distance covers it
            msg.linear.x = float(distance) / COMMAND_DURATION
            self.publish_motion(msg)
            return f"Moved forward {distance} units"

        @tool
        def rotate(angle: float) -> str:
            """Rotate turtle by specified angle in degrees (positive for counterclockwise)."""
            msg = Twist()
            msg.angular.z = math.radians(float(angle)) / COMMAND_DURATION
            self.publish_motion(msg)
            return f"Rotated {angle} degrees"

        @tool
        def get_pose() -> str:
            """Get current pose of the turtle."""
            return f"x: {self.turtle_pose.x:.2f}, y: {self.turtle_pose.y:.2f}, theta: {math.degrees(self.turtle_pose.theta):.2f} degrees"

        system_prompt = """You are a turtle control assistant for ROS 2 turtlesim.
        You can control the turtle using these commands:
        - move_forward(distance): Move turtle forward by specified distance
        - rotate(angle): Rotate turtle by specified angle in degrees
        - get_pose(): Get current position and orientation of turtle
        
        Return only the necessary actions and their results. e.g
        Human: Move the turtle forward 2 units
        AI: Moving forward 2 units"""

        # setup the toolkit with the class methods
        self.toolkit = [move_forward, rotate, get_pose]

        # Choose the LLM that will drive the agent
        self.llm = ChatOllama(model="qwen3:8b", temperature=0)

        # Construct the unified, modern tool-calling agent runner directly
        # In the modern interface, create_agent returns a self-contained runtime graph
        self.agent_executor = create_agent(self.llm, tools=self.toolkit, system_prompt=system_prompt)

        # Create the subscriber for prompts. Prompts run on a background thread so
        # pose updates keep arriving while the agent is working on a prompt.
        self.subscription = self.create_subscription(
            String,
            'prompt',
            prompt_worker(self.prompt_callback),
            10
        )

    def publish_motion(self, msg):
        """Publish a velocity command and wait until turtlesim has finished it."""
        with self.motion_lock:
            self.cmd_vel_pub.publish(msg)
            time.sleep(COMMAND_DURATION + 0.2)

    def pose_callback(self, msg):
        """Callback to update turtle's pose"""
        self.turtle_pose = msg

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
    run_node(ROS2AIAgent, args)


if __name__ == '__main__':
    main()
