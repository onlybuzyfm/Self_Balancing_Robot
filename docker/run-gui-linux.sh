#!/usr/bin/env bash
set -euo pipefail

IMAGE="tumbller-gazebo:jazzy"

docker build -t "$IMAGE" .

if command -v xhost >/dev/null 2>&1; then
  xhost +local:docker >/dev/null || true
fi

XDG_DIR="${XDG_RUNTIME_DIR:-/tmp}"
DISPLAY_VALUE="${DISPLAY:-:0}"
WAYLAND_VALUE="${WAYLAND_DISPLAY:-wayland-0}"

docker run --rm -it \
  --name tumbller_gazebo_pid_gui \
  --net=host \
  --ipc=host \
  -e DISPLAY="$DISPLAY_VALUE" \
  -e WAYLAND_DISPLAY="$WAYLAND_VALUE" \
  -e XDG_RUNTIME_DIR="$XDG_DIR" \
  -e QT_X11_NO_MITSHM=1 \
  -e LIBGL_ALWAYS_SOFTWARE="${LIBGL_ALWAYS_SOFTWARE:-1}" \
  -e ROS_DOMAIN_ID="${ROS_DOMAIN_ID:-42}" \
  -v /tmp/.X11-unix:/tmp/.X11-unix:rw \
  -v "$XDG_DIR":"$XDG_DIR":rw \
  -v "$PWD":/workspaces/tumbller_ws/src/tumbller_gazebo \
  -w /workspaces/tumbller_ws \
  "$IMAGE" \
  ros2 launch tumbller_gazebo sim_pid.launch.py