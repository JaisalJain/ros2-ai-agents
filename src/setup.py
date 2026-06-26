from setuptools import setup, find_packages
import os
from glob import glob

package_name = 'ros2_agent'

setup(
    name=package_name,
    version='0.0.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.py')),
        (os.path.join('share', package_name, 'config'), glob('config/*')),
        #(os.path.join('lib', package_name), glob('ros2_agent/*.py')),

    ],
    install_requires=['setuptools','langchain','langchain-openai'],
    zip_safe=True,
    maintainer='Jaisal',
    maintainer_email='jaisaljain345@gmail.com',
    description='ROS 2 AI agent',
    license='TODO: License declaration',
    #tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'ros2_ai_agent_basic = ros2_agent.ros2_ai_agent_basic:main',            
            'ros2_ai_agent_basic_tools = ros2_agent.ros2_ai_agent_basic_tools:main',            
            'ros2_ai_agent_turtlesim = ros2_agent.ros2_ai_agent_turtlesim:main',
'ros2_ai_agent_turtlebo3_nav2 = ros2_agent.ros2_ai_agent_turtlebo3_nav2:main',
            'ros2_ai_agent_moveit2 = ros2_agent.ros2_ai_agent_ur_moveit2:main',            
        ],
    },
)
