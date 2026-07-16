FROM osrf/ros:jazzy-desktop-full

ENV DEBIAN_FRONTEND=noninteractive
SHELL ["/bin/bash", "-c"]

RUN apt-get update && apt-get install -y --no-install-recommends \
    bash-completion \
    build-essential \
    git \
    nano \
    python3-colcon-common-extensions \
    python3-pip \
    python3-rosdep \
    python3-vcstool \
    ros-jazzy-ros-gz \
    ros-jazzy-robot-state-publisher \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspaces/tumbller_ws
COPY . /workspaces/tumbller_ws/src/tumbller_gazebo

RUN source /opt/ros/jazzy/setup.bash \
    && colcon build --symlink-install --packages-select tumbller_gazebo

COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh /workspaces/tumbller_ws/src/tumbller_gazebo/docker/*.sh

ENTRYPOINT ["/entrypoint.sh"]
CMD ["ros2", "launch", "tumbller_gazebo", "sim_headless.launch.py"]