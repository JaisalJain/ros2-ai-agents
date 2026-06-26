#!/usr/bin/env python3

"""
This script defines a ROS 2 node that integrates with Ollama's language model to interact with a ROS 2 system.
The node subscribes to a topic and processes incoming messages using an AI agent equipped with predefined tools.

Dependencies:
    - Ollama integration: langchain_ollama, langchain
    - rclpy (rclpy, Node)
    - std_msgs.msg (String)
    - ament_index_python.packages (get_package_share_directory)
    - pathlib (Path)
"""

import os
from pathlib import Path

import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from ament_index_python.packages import get_package_share_directory

from langchain_ollama import ChatOllama
from langchain.agents import create_agent
from langchain.tools import tool

class ROS2AIAgent(Node):
    def __init__(self):
        super().__init__('ros2_ai_agent')
        self.get_logger().info('ROS2 AI Agent has been started')

        # Create tools
        self.get_ros_distro_tool = tool(self.get_ros_distro)
        self.get_domain_id_tool = tool(self.get_domain_id)

        # Define a clean system instruction string
        system_prompt = """You are a ROS 2 system information assistant. You can check ROS 2 system status using these commands:
- get_ros_distro(): Get the current ROS distribution name
- get_domain_id(): Get the current ROS_DOMAIN_ID
Return only the necessary information and results.
e.g Human: What ROS distribution am I using?
AI: Current ROS distribution: humble
Human: What is my ROS domain ID?
AI: Current ROS domain ID: 0 """

        #share_dir = get_package_share_directory('ros2_agent')
        #config_dir = share_dir + '/config' + '/openai.env'
        #load_dotenv(Path(config_dir))

        # Setup the toolkit with both tools
        self.toolkit = [self.get_ros_distro_tool, self.get_domain_id_tool]

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

    def get_ros_distro(self) -> str:
        """Get the current ROS distribution name."""
        try:
            ros_distro = os.environ.get('ROS_DISTRO')
            if (ros_distro):
                return f"Current ROS distribution: {ros_distro}"
            else:
                return "ROS distribution environment variable (ROS_DISTRO) not set"
        except Exception as e:
            return f"Error getting ROS distribution: {str(e)}"

    def get_domain_id(self) -> str:
        """Get the current ROS domain ID."""
        try:
            domain_id = os.environ.get('ROS_DOMAIN_ID', '0')  # Default is 0 if not set
            return f"Current ROS domain ID: {domain_id}"
        except Exception as e:
            return f"Error getting ROS domain ID: {str(e)}"

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
        rclpy.try_shutdown()

if __name__ == '__main__':
    main()
