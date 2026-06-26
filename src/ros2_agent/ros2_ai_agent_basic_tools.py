#!/usr/bin/env python3

"""
This script defines a ROS2 node that integrates with Ollama's language model to interact with a ROS 2 system.
The node subscribes to a topic and processes incoming messages using an AI agent with predefined tools.

Classes:
    ROS2AIAgent(Node): A ROS2 node that subscribes to a topic and uses an AI agent to process messages.

Methods:
    prompt_callback(msg: String): Callback function to process incoming messages.
    list_topics() -> str: Lists all available ROS 2 topics.
    list_nodes() -> str: Lists all running ROS 2 nodes.
    list_services() -> str: Lists all available ROS 2 services.
    list_actions() -> str: Lists all available ROS 2 actions.
    main(args=None): Initializes and spins the ROS2 node.

Dependencies:
    - std_msgs.msg (String)
    - rclpy (rclpy, Node)
    - ament_index_python.packages (get_package_share_directory)
    - pathlib (Path)
    - Ollama integration: langchain_ollama, langchain
    - langchain.tools (tool)
    - subprocess
"""
import subprocess
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

        # Create tools using class methods
        self.list_topics_tool = tool(self.list_topics)
        self.list_nodes_tool = tool(self.list_nodes)
        self.list_services_tool = tool(self.list_services)
        self.list_actions_tool = tool(self.list_actions)

        system_prompt = """You are a ROS 2 system information assistant.
        You can check ROS 2 system status using these commands:
        - list_topics(): List all available ROS 2 topics
        - list_nodes(): List all running ROS 2 nodes
        - list_services(): List all available ROS 2 services
        - list_actions(): List all available ROS 2 actions
        
        Return only the necessary information and results. e.g
        Human: Show me all running nodes
        AI: Here are the running ROS 2 nodes: [node list]"""

        #share_dir = get_package_share_directory('ros2_agent')
        #config_dir = share_dir + '/config' + '/openai.env'
        #load_dotenv(Path(config_dir))

        # setup the toolkit with the decorated class methods
        self.toolkit = [
            self.list_topics_tool,
            self.list_nodes_tool,
            self.list_services_tool,
            self.list_actions_tool
        ]

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

    def list_topics(self) -> str:
        """List all available ROS 2 topics."""
        try:
            result = subprocess.run(['ros2', 'topic', 'list'], 
                                 capture_output=True, text=True, check=True)
            return f"Available ROS 2 topics:\n{result.stdout}"
        except subprocess.CalledProcessError as e:
            return f"Error listing topics: {str(e)}"

    def list_nodes(self) -> str:
        """List all running ROS 2 nodes."""
        try:
            result = subprocess.run(['ros2', 'node', 'list'], 
                                 capture_output=True, text=True, check=True)
            return f"Running ROS 2 nodes:\n{result.stdout}"
        except subprocess.CalledProcessError as e:
            return f"Error listing nodes: {str(e)}"

    def list_services(self) -> str:
        """List all available ROS 2 services."""
        try:
            result = subprocess.run(['ros2', 'service', 'list'], 
                                 capture_output=True, text=True, check=True)
            return f"Available ROS 2 services:\n{result.stdout}"
        except subprocess.CalledProcessError as e:
            return f"Error listing services: {str(e)}"

    def list_actions(self) -> str:
        """List all available ROS 2 actions."""
        try:
            result = subprocess.run(['ros2', 'action', 'list'], 
                                 capture_output=True, text=True, check=True)
            return f"Available ROS 2 actions:\n{result.stdout}"
        except subprocess.CalledProcessError as e:
            return f"Error listing actions: {str(e)}"

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
