#!/usr/bin/env python3
import math

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


def yaw_to_quaternion(yaw: float) -> tuple[float, float, float, float]:
    half = 0.5 * yaw
    return 0.0, 0.0, math.sin(half), math.cos(half)


class BalanceObserver(Node):
    def __init__(self) -> None:
        super().__init__("balance_observer")

        self.declare_parameter("wheel_radius_m", 0.034)
        self.declare_parameter("wheel_separation_m", 0.132)
        self.declare_parameter("publish_rate_hz", 50.0)
        self.declare_parameter("odom_frame", "odom")
        self.declare_parameter("base_frame", "base_link")

        self.wheel_radius = float(self.get_parameter("wheel_radius_m").value)
        self.wheel_separation = float(self.get_parameter("wheel_separation_m").value)
        self.odom_frame = str(self.get_parameter("odom_frame").value)
        self.base_frame = str(self.get_parameter("base_frame").value)

        self.left_speed = 0.0
        self.right_speed = 0.0
        self.left_pos = 0.0
        self.right_pos = 0.0
        self.x = 0.0
        self.y = 0.0
        self.yaw = 0.0
        self.pitch = 0.0
        self.pitch_rate = 0.0
        self.last_time = self.get_clock().now()

        self.create_subscription(Imu, "/tumbller/imu", self.on_imu, 20)
        self.create_subscription(Float64, "/tumbller/left_wheel/velocity_cmd", self.on_left_cmd, 20)
        self.create_subscription(Float64, "/tumbller/right_wheel/velocity_cmd", self.on_right_cmd, 20)

        self.odom_pub = self.create_publisher(Odometry, "/tumbller/odom", 10)
        self.joint_pub = self.create_publisher(JointState, "/joint_states", 10)
        self.pitch_pub = self.create_publisher(Float64, "/tumbller/observer/pitch_rad", 10)
        self.pitch_rate_pub = self.create_publisher(Float64, "/tumbller/observer/pitch_rate_rad_s", 10)
        self.base_velocity_pub = self.create_publisher(Float64, "/tumbller/observer/base_velocity_m_s", 10)
        self.left_cmd_pub = self.create_publisher(Float64, "/tumbller/observer/left_wheel_speed_rad_s", 10)
        self.right_cmd_pub = self.create_publisher(Float64, "/tumbller/observer/right_wheel_speed_rad_s", 10)

        period = 1.0 / float(self.get_parameter("publish_rate_hz").value)
        self.create_timer(period, self.on_timer)
        self.get_logger().info(
            f"Balance observer ready: r={self.wheel_radius:.3f} m, track={self.wheel_separation:.3f} m"
        )

    def on_imu(self, msg: Imu) -> None:
        q = msg.orientation
        self.pitch = pitch_from_quaternion(q.x, q.y, q.z, q.w)
        self.pitch_rate = msg.angular_velocity.y

    def on_left_cmd(self, msg: Float64) -> None:
        self.left_speed = msg.data

    def on_right_cmd(self, msg: Float64) -> None:
        self.right_speed = msg.data

    def reset_if_needed(self, now) -> bool:
        if (now - self.last_time).nanoseconds >= 0:
            return False
        self.left_pos = 0.0
        self.right_pos = 0.0
        self.x = 0.0
        self.y = 0.0
        self.yaw = 0.0
        self.last_time = now
        self.get_logger().info("Simulation reset detected; odometry cleared.")
        return True

    def on_timer(self) -> None:
        now = self.get_clock().now()
        if self.reset_if_needed(now):
            return

        dt = max((now - self.last_time).nanoseconds * 1e-9, 1e-4)
        self.last_time = now

        left_linear = self.left_speed * self.wheel_radius
        right_linear = self.right_speed * self.wheel_radius
        linear_velocity = 0.5 * (left_linear + right_linear)
        yaw_rate = (right_linear - left_linear) / self.wheel_separation

        self.left_pos += self.left_speed * dt
        self.right_pos += self.right_speed * dt
        self.yaw += yaw_rate * dt
        self.x += linear_velocity * math.cos(self.yaw) * dt
        self.y += linear_velocity * math.sin(self.yaw) * dt

        self.publish_odometry(now, linear_velocity, yaw_rate)
        self.publish_joint_states(now)
        self.publish_debug(linear_velocity)

    def publish_odometry(self, now, linear_velocity: float, yaw_rate: float) -> None:
        qx, qy, qz, qw = yaw_to_quaternion(self.yaw)
        msg = Odometry()
        msg.header.stamp = now.to_msg()
        msg.header.frame_id = self.odom_frame
        msg.child_frame_id = self.base_frame
        msg.pose.pose.position.x = self.x
        msg.pose.pose.position.y = self.y
        msg.pose.pose.position.z = 0.0
        msg.pose.pose.orientation.x = qx
        msg.pose.pose.orientation.y = qy
        msg.pose.pose.orientation.z = qz
        msg.pose.pose.orientation.w = qw
        msg.twist.twist.linear.x = linear_velocity
        msg.twist.twist.angular.y = self.pitch_rate
        msg.twist.twist.angular.z = yaw_rate
        self.odom_pub.publish(msg)

    def publish_joint_states(self, now) -> None:
        msg = JointState()
        msg.header.stamp = now.to_msg()
        msg.name = ["left_wheel_joint", "right_wheel_joint"]
        msg.position = [self.left_pos, self.right_pos]
        msg.velocity = [self.left_speed, self.right_speed]
        self.joint_pub.publish(msg)

    def publish_debug(self, linear_velocity: float) -> None:
        self.publish_float(self.pitch_pub, self.pitch)
        self.publish_float(self.pitch_rate_pub, self.pitch_rate)
        self.publish_float(self.base_velocity_pub, linear_velocity)
        self.publish_float(self.left_cmd_pub, self.left_speed)
        self.publish_float(self.right_cmd_pub, self.right_speed)

    def publish_float(self, publisher, value: float) -> None:
        msg = Float64()
        msg.data = value
        publisher.publish(msg)


def main() -> None:
    rclpy.init()
    node = BalanceObserver()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()