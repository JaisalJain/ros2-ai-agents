#!/usr/bin/env bash
# Allow ROS 2's system Python to discover packages installed in the virtual environment.

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

source "$PROJECT_ROOT/.venv/bin/activate"
source /opt/ros/jazzy/setup.bash

export PYTHONPATH="$PROJECT_ROOT/.venv/lib/python3.12/site-packages:$PYTHONPATH"

source "$PROJECT_ROOT/install/setup.bash"
