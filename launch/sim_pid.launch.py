from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, SetEnvironmentVariable
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import EnvironmentVariable
from launch_ros.actions import Node

import os


def generate_launch_description():
    share_dir = get_package_share_directory("tumbller_gazebo")
    ros_gz_sim_dir = get_package_share_directory("ros_gz_sim")
    models_dir = os.path.join(share_dir, "models")
    world_path = os.path.join(share_dir, "worlds", "tumbller_lab.sdf")
    bridge_config = os.path.join(share_dir, "config", "bridge.yaml")
    controller_params = os.path.join(share_dir, "config", "pid_params.yaml")
    observer_params = os.path.join(share_dir, "config", "observer_params.yaml")
    logger_params = os.path.join(share_dir, "config", "logger_params.yaml")

    gz_sim = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(ros_gz_sim_dir, "launch", "gz_sim.launch.py")
        ),
        launch_arguments={"gz_args": f"-r {world_path}"}.items(),
    )

    bridge = Node(
        package="ros_gz_bridge",
        executable="parameter_bridge",
        parameters=[{"config_file": bridge_config}],
        output="screen",
    )

    controller = Node(
        package="tumbller_gazebo",
        executable="balance_controller.py",
        parameters=[controller_params, {"use_sim_time": True}],
        output="screen",
    )


    observer = Node(
        package="tumbller_gazebo",
        executable="balance_observer.py",
        parameters=[observer_params, {"use_sim_time": True}],
        output="screen",
    )

    logger = Node(
        package="tumbller_gazebo",
        executable="balance_csv_logger.py",
        parameters=[logger_params, {"use_sim_time": True}],
        output="screen",
    )
    return LaunchDescription(
        [
            SetEnvironmentVariable(
                name="GZ_SIM_RESOURCE_PATH",
                value=[models_dir, os.pathsep, EnvironmentVariable("GZ_SIM_RESOURCE_PATH")],
            ),
            gz_sim,
            bridge,
            controller,
            observer,
            logger,
        ]
    )