#!/usr/bin/env bash
set -e

source /opt/ros/jazzy/setup.bash

if [ -f /workspaces/tumbller_ws/install/setup.bash ]; then
  source /workspaces/tumbller_ws/install/setup.bash
fi

export GZ_SIM_RESOURCE_PATH="/workspaces/tumbller_ws/src/tumbller_gazebo/models:${GZ_SIM_RESOURCE_PATH:-}"

exec "$@"