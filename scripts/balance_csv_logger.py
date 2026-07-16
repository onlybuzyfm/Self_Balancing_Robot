#!/usr/bin/env python3
import csv
import math
from datetime import datetime
from pathlib import Path

import rclpy
from nav_msgs.msg import Odometry
from rclpy.node import Node
from sensor_msgs.msg import Imu, JointState
from std_msgs.msg import Float64


def pitch_from_quaternion(x: float, y: float, z: float, w: float) -> float:
    sinp = 2.0 * (w * y - z * x)
    if abs(sinp) >= 1.0:
        return math.copysign(math.pi / 2.0, sinp)
    return math.asin(sinp)


def yaw_from_quaternion(x: float, y: float, z: float, w: float) -> float:
    siny_cosp = 2.0 * (w * z + x * y)
    cosy_cosp = 1.0 - 2.0 * (y * y + z * z)
    return math.atan2(siny_cosp, cosy_cosp)


class BalanceCsvLogger(Node):
    def __init__(self) -> None:
        super().__init__("balance_csv_logger")

        self.declare_parameter("output_dir", "/workspaces/tumbller_ws/src/tumbller_gazebo/data/logs")
        self.declare_parameter("filename_prefix", "balance_run")
        self.declare_parameter("sample_rate_hz", 50.0)
        self.declare_parameter("flush_every_rows", 10)

        output_dir = Path(str(self.get_parameter("output_dir").value))
        output_dir.mkdir(parents=True, exist_ok=True)
        prefix = str(self.get_parameter("filename_prefix").value)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.csv_path = output_dir / f"{prefix}_{stamp}.csv"
        self.flush_every_rows = int(self.get_parameter("flush_every_rows").value)
        self.rows_since_flush = 0

        self.imu_pitch = 0.0
        self.imu_pitch_rate = 0.0
        self.imu_accel_x = 0.0
        self.imu_accel_z = 0.0
        self.controller_wheel_cmd = 0.0
        self.controller_base_accel = 0.0
        self.controller_base_position = 0.0
        self.left_wheel_speed = 0.0
        self.right_wheel_speed = 0.0
        self.real_left_wheel_speed = 0.0
        self.real_right_wheel_speed = 0.0
        self.observer_pitch = 0.0
        self.observer_pitch_rate = 0.0
        self.observer_base_velocity = 0.0
        self.odom_x = 0.0
        self.odom_y = 0.0
        self.odom_yaw = 0.0
        self.odom_linear_x = 0.0
        self.odom_yaw_rate = 0.0

        self.csv_file = self.csv_path.open("w", newline="", encoding="utf-8")
        self.writer = csv.DictWriter(self.csv_file, fieldnames=self.fieldnames())
        self.writer.writeheader()

        self.create_subscription(Imu, "/tumbller/imu", self.on_imu, 20)
        self.create_subscription(Float64, "/tumbller/debug/wheel_cmd_rad_s", self.on_controller_cmd, 20)
        self.create_subscription(Float64, "/tumbller/debug/base_accel_m_s2", self.on_controller_accel, 20)
        self.create_subscription(Float64, "/tumbller/debug/base_position_m", self.on_controller_position, 20)
        self.create_subscription(Float64, "/tumbller/observer/left_wheel_speed_rad_s", self.on_left_speed, 20)
        self.create_subscription(Float64, "/tumbller/observer/right_wheel_speed_rad_s", self.on_right_speed, 20)
        self.create_subscription(JointState, "/tumbller/gz_joint_states", self.on_gz_joint_states, 20)
        self.create_subscription(Float64, "/tumbller/observer/pitch_rad", self.on_observer_pitch, 20)
        self.create_subscription(Float64, "/tumbller/observer/pitch_rate_rad_s", self.on_observer_pitch_rate, 20)
        self.create_subscription(Float64, "/tumbller/observer/base_velocity_m_s", self.on_observer_base_velocity, 20)
        self.create_subscription(Odometry, "/tumbller/odom", self.on_odom, 20)

        period = 1.0 / float(self.get_parameter("sample_rate_hz").value)
        self.create_timer(period, self.on_timer)
        self.get_logger().info(f"Logging balance data to {self.csv_path}")

    def fieldnames(self) -> list[str]:
        return [
            "ros_time_s",
            "imu_pitch_rad",
            "imu_pitch_rate_rad_s",
            "imu_accel_x_m_s2",
            "imu_accel_z_m_s2",
            "controller_wheel_cmd_rad_s",
            "controller_base_accel_m_s2",
            "controller_base_position_m",
            "left_wheel_speed_rad_s",
            "right_wheel_speed_rad_s",
            "real_left_wheel_speed_rad_s",
            "real_right_wheel_speed_rad_s",
            "observer_pitch_rad",
            "observer_pitch_rate_rad_s",
            "observer_base_velocity_m_s",
            "odom_x_m",
            "odom_y_m",
            "odom_yaw_rad",
            "odom_linear_x_m_s",
            "odom_yaw_rate_rad_s",
        ]

    def on_imu(self, msg: Imu) -> None:
        q = msg.orientation
        self.imu_pitch = pitch_from_quaternion(q.x, q.y, q.z, q.w)
        self.imu_pitch_rate = msg.angular_velocity.y
        self.imu_accel_x = msg.linear_acceleration.x
        self.imu_accel_z = msg.linear_acceleration.z

    def on_controller_cmd(self, msg: Float64) -> None:
        self.controller_wheel_cmd = msg.data

    def on_controller_accel(self, msg: Float64) -> None:
        self.controller_base_accel = msg.data

    def on_controller_position(self, msg: Float64) -> None:
        self.controller_base_position = msg.data

    def on_left_speed(self, msg: Float64) -> None:
        self.left_wheel_speed = msg.data

    def on_right_speed(self, msg: Float64) -> None:
        self.right_wheel_speed = msg.data

    def on_gz_joint_states(self, msg: JointState) -> None:
        for index, name in enumerate(msg.name):
            if index >= len(msg.velocity):
                continue
            if name == "left_wheel_joint":
                self.real_left_wheel_speed = msg.velocity[index]
            elif name == "right_wheel_joint":
                self.real_right_wheel_speed = msg.velocity[index]

    def on_observer_pitch(self, msg: Float64) -> None:
        self.observer_pitch = msg.data

    def on_observer_pitch_rate(self, msg: Float64) -> None:
        self.observer_pitch_rate = msg.data

    def on_observer_base_velocity(self, msg: Float64) -> None:
        self.observer_base_velocity = msg.data

    def on_odom(self, msg: Odometry) -> None:
        self.odom_x = msg.pose.pose.position.x
        self.odom_y = msg.pose.pose.position.y
        q = msg.pose.pose.orientation
        self.odom_yaw = yaw_from_quaternion(q.x, q.y, q.z, q.w)
        self.odom_linear_x = msg.twist.twist.linear.x
        self.odom_yaw_rate = msg.twist.twist.angular.z

    def on_timer(self) -> None:
        now = self.get_clock().now()
        self.writer.writerow(
            {
                "ros_time_s": now.nanoseconds * 1e-9,
                "imu_pitch_rad": self.imu_pitch,
                "imu_pitch_rate_rad_s": self.imu_pitch_rate,
                "imu_accel_x_m_s2": self.imu_accel_x,
                "imu_accel_z_m_s2": self.imu_accel_z,
                "controller_wheel_cmd_rad_s": self.controller_wheel_cmd,
                "controller_base_accel_m_s2": self.controller_base_accel,
                "controller_base_position_m": self.controller_base_position,
                "left_wheel_speed_rad_s": self.left_wheel_speed,
                "right_wheel_speed_rad_s": self.right_wheel_speed,
                "real_left_wheel_speed_rad_s": self.real_left_wheel_speed,
                "real_right_wheel_speed_rad_s": self.real_right_wheel_speed,
                "observer_pitch_rad": self.observer_pitch,
                "observer_pitch_rate_rad_s": self.observer_pitch_rate,
                "observer_base_velocity_m_s": self.observer_base_velocity,
                "odom_x_m": self.odom_x,
                "odom_y_m": self.odom_y,
                "odom_yaw_rad": self.odom_yaw,
                "odom_linear_x_m_s": self.odom_linear_x,
                "odom_yaw_rate_rad_s": self.odom_yaw_rate,
            }
        )
        self.rows_since_flush += 1
        if self.rows_since_flush >= self.flush_every_rows:
            self.csv_file.flush()
            self.rows_since_flush = 0

    def destroy_node(self) -> bool:
        try:
            self.csv_file.flush()
            self.csv_file.close()
        finally:
            return super().destroy_node()


def main() -> None:
    rclpy.init()
    node = BalanceCsvLogger()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()