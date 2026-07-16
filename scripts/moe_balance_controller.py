#!/usr/bin/env python3
import math
from dataclasses import dataclass

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Imu
from std_msgs.msg import Float64


@dataclass
class Expert:
    kp: float
    kd: float
    ki: float = 0.0
    integral: float = 0.0

    def command(self, tilt: float, tilt_rate: float, dt: float) -> float:
        self.integral += tilt * dt
        return self.kp * tilt + self.kd * tilt_rate + self.ki * self.integral


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def pitch_from_quaternion(x: float, y: float, z: float, w: float) -> float:
    sinp = 2.0 * (w * y - z * x)
    if abs(sinp) >= 1.0:
        return math.copysign(math.pi / 2.0, sinp)
    return math.asin(sinp)


class MoeBalanceController(Node):
    def __init__(self) -> None:
        super().__init__("moe_balance_controller")

        self.declare_parameter("control_rate_hz", 100.0)
        self.declare_parameter("max_wheel_speed_rad_s", 18.0)
        self.declare_parameter("max_tilt_rad", 1.25)
        self.declare_parameter("deadband_rad", 0.015)
        self.declare_parameter("command_sign", -1.0)
        self.declare_parameter("recovery_tilt_rad", 0.22)
        self.declare_parameter("damping_rate_rad_s", 1.8)
        self.declare_parameter("balance_kp", 34.0)
        self.declare_parameter("balance_kd", 1.25)
        self.declare_parameter("balance_ki", 0.0)
        self.declare_parameter("recovery_kp", 54.0)
        self.declare_parameter("recovery_kd", 1.8)
        self.declare_parameter("recovery_ki", 0.0)
        self.declare_parameter("damping_kp", 18.0)
        self.declare_parameter("damping_kd", 2.5)
        self.declare_parameter("damping_ki", 0.0)

        self.balance = Expert(
            kp=float(self.get_parameter("balance_kp").value),
            kd=float(self.get_parameter("balance_kd").value),
            ki=float(self.get_parameter("balance_ki").value),
        )
        self.recovery = Expert(
            kp=float(self.get_parameter("recovery_kp").value),
            kd=float(self.get_parameter("recovery_kd").value),
            ki=float(self.get_parameter("recovery_ki").value),
        )
        self.damping = Expert(
            kp=float(self.get_parameter("damping_kp").value),
            kd=float(self.get_parameter("damping_kd").value),
            ki=float(self.get_parameter("damping_ki").value),
        )

        self.max_wheel_speed = float(self.get_parameter("max_wheel_speed_rad_s").value)
        self.max_tilt = float(self.get_parameter("max_tilt_rad").value)
        self.deadband = float(self.get_parameter("deadband_rad").value)
        self.command_sign = float(self.get_parameter("command_sign").value)
        self.recovery_tilt = float(self.get_parameter("recovery_tilt_rad").value)
        self.damping_rate = float(self.get_parameter("damping_rate_rad_s").value)

        self.tilt = 0.0
        self.tilt_rate = 0.0
        self.last_time = self.get_clock().now()

        self.left_pub = self.create_publisher(Float64, "/tumbller/left_wheel/velocity_cmd", 10)
        self.right_pub = self.create_publisher(Float64, "/tumbller/right_wheel/velocity_cmd", 10)
        self.create_subscription(Imu, "/tumbller/imu", self.on_imu, 20)

        period = 1.0 / float(self.get_parameter("control_rate_hz").value)
        self.create_timer(period, self.on_timer)
        self.get_logger().info(f"MoE balance controller ready. command_sign={self.command_sign}")

    def on_imu(self, msg: Imu) -> None:
        q = msg.orientation
        self.tilt = pitch_from_quaternion(q.x, q.y, q.z, q.w)
        self.tilt_rate = msg.angular_velocity.y

    def gate(self, tilt: float, tilt_rate: float) -> tuple[float, float, float]:
        recovery_weight = clamp(abs(tilt) / self.recovery_tilt, 0.0, 1.0)
        damping_weight = clamp(abs(tilt_rate) / self.damping_rate, 0.0, 1.0)
        balance_weight = max(0.0, 1.0 - 0.65 * recovery_weight - 0.35 * damping_weight)
        total = balance_weight + recovery_weight + damping_weight
        return balance_weight / total, recovery_weight / total, damping_weight / total

    def on_timer(self) -> None:
        now = self.get_clock().now()
        dt = max((now - self.last_time).nanoseconds * 1e-9, 1e-4)
        self.last_time = now

        if abs(self.tilt) > self.max_tilt:
            self.publish_wheel_speed(0.0)
            self.get_logger().warn(
                f"Tilt {self.tilt:.3f} rad exceeds safety limit {self.max_tilt:.3f}; stopping wheels.",
                throttle_duration_sec=1.0,
            )
            return

        tilt = 0.0 if abs(self.tilt) < self.deadband else self.tilt
        wb, wr, wd = self.gate(tilt, self.tilt_rate)

        raw_cmd = (
            wb * self.balance.command(tilt, self.tilt_rate, dt)
            + wr * self.recovery.command(tilt, self.tilt_rate, dt)
            + wd * self.damping.command(tilt, self.tilt_rate, dt)
        )
        cmd = self.command_sign * raw_cmd

        self.publish_wheel_speed(clamp(cmd, -self.max_wheel_speed, self.max_wheel_speed))

    def publish_wheel_speed(self, speed: float) -> None:
        msg = Float64()
        msg.data = speed
        self.left_pub.publish(msg)
        self.right_pub.publish(msg)


def main() -> None:
    rclpy.init()
    node = MoeBalanceController()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()