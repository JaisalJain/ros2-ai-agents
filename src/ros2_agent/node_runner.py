"""Shared helpers to run the agent nodes."""

import queue
import threading

import rclpy
from rclpy.executors import ExternalShutdownException, SingleThreadedExecutor


def prompt_worker(handle_prompt):
    """Return a subscription callback that hands each prompt to a background thread.

    Prompts are handled one at a time, in order, while the node keeps spinning, so
    pose, TF and action callbacks are still processed while the LLM is working.
    """
    prompts = queue.Queue()

    def work():
        while True:
            handle_prompt(prompts.get())

    threading.Thread(target=work, daemon=True).start()
    return prompts.put


def run_node(node_class, args=None):
    """Create node_class() and spin it until Ctrl+C, then shut down cleanly."""
    rclpy.init(args=args)
    node = None
    executor = SingleThreadedExecutor()
    try:
        node = node_class()
        executor.add_node(node)
        # Spin in short steps so Ctrl+C is noticed even when no message arrives
        # to wake the executor (e.g. while a prompt is running)
        while rclpy.ok():
            executor.spin_once(timeout_sec=0.5)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    except Exception:
        # Errors caused by Ctrl+C shutting ROS down mid-spin are not failures
        if rclpy.ok():
            raise
    finally:
        executor.shutdown()
        if node is not None:
            node.destroy_node()
        rclpy.try_shutdown()
