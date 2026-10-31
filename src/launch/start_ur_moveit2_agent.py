from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, TimerAction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory
import os

def generate_launch_description():
    # Include the UR MoveIt2 simulation launch file
    ur_launch_file_dir = os.path.join(get_package_share_directory('ur_simulation_gz'), 'launch')
    
    # Simulate a UR5e and start the trajectory controller that MoveIt sends motions to
    # (ur_moveit_config uses scaled_joint_trajectory_controller by default)
    ur_moveit_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([ur_launch_file_dir, '/ur_sim_moveit.launch.py']),
        launch_arguments={
            'ur_type': 'ur5e',
            'initial_joint_controller': 'scaled_joint_trajectory_controller'
        }.items()
    )

    # Define the AI agent node with a delay
    delayed_agent = TimerAction(
        period=10.0,  # 10 second delay
        actions=[
            Node(
                package='ros2_agent',
                executable='ros2_ai_agent_moveit2',
                name='ros2_ai_agent_moveit2',
                output='screen',
                emulate_tty=True,
            )
        ]
    )

    return LaunchDescription([
        ur_moveit_launch,
        delayed_agent
    ])
