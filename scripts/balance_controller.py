#!/usr/bin/env python3
import math

import rclpy
from rcl_interfaces.msg import ParameterType
from rclpy.node import Node
from sensor_msgs.msg import Imu
from std_msgs.msg import Float64


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def pitch_from_quaternion(x: float, y: float, z: float, w: float) -> float:
    sinp = 2.0 * (w * y - z * x)
    if abs(sinp) >= 1.0:
        return math.copysign(math.pi / 2.0, sinp)
    return math.asin(sinp)


class BalanceController(Node):
    def __init__(self) -> None:
        super().__init__("balance_controller")

        for name in [
            "control_rate_hz",
            "wheel_radius_m",
            "tilt_accel_gain_m_s2_per_rad",
            "tilt_rate_accel_gain_m_s2_per_rad_s",
            "position_kp",
            "velocity_kd",
            "upright_tilt_window_rad",
            "upright_rate_window_rad_s",
            "upright_position_kp",
            "upright_velocity_kd",
            "max_position_tilt_rad",
            "max_base_velocity_m_s",
            "max_base_accel_m_s2",
            "max_wheel_speed_rad_s",
            "max_wheel_accel_rad_s2",
            "max_tilt_rad",
            "deadband_rad",
            "rate_deadband_rad_s",
            "pitch_filter_alpha",
            "rate_filter_alpha",
            "command_sign",
        ]:
            self.declare_parameter(name)
        self.declare_parameter("publish_debug", True)

        self.control_rate_hz = self.numeric_parameter("control_rate_hz", 100.0)
        self.wheel_radius = self.numeric_parameter("wheel_radius_m", 0.034)
        self.tilt_accel_gain = self.numeric_parameter("tilt_accel_gain_m_s2_per_rad", 28.0)
        self.tilt_rate_accel_gain = self.numeric_parameter("tilt_rate_accel_gain_m_s2_per_rad_s", 6.0)
        self.position_kp = self.numeric_parameter("position_kp", 0.10)
        self.velocity_kd = self.numeric_parameter("velocity_kd", 0.15)
        self.upright_tilt_window = self.numeric_parameter("upright_tilt_window_rad", 0.035)
        self.upright_rate_window = self.numeric_parameter("upright_rate_window_rad_s", 0.12)
        self.upright_position_kp = self.numeric_parameter("upright_position_kp", 0.80)
        self.upright_velocity_kd = self.numeric_parameter("upright_velocity_kd", 1.60)
        self.max_position_tilt = self.numeric_parameter("max_position_tilt_rad", 0.12)
        self.max_base_velocity = self.numeric_parameter("max_base_velocity_m_s", 0.64)
        self.max_base_accel = self.numeric_parameter("max_base_accel_m_s2", 4.5)
        self.max_wheel_speed = self.numeric_parameter("max_wheel_speed_rad_s", 18.85)
        self.max_wheel_accel = self.numeric_parameter("max_wheel_accel_rad_s2", 140.0)
        self.max_tilt = self.numeric_parameter("max_tilt_rad", 1.25)
        self.deadband = self.numeric_parameter("deadband_rad", 0.012)
        self.rate_deadband = self.numeric_parameter("rate_deadband_rad_s", 0.030)
        self.pitch_filter_alpha = self.numeric_parameter("pitch_filter_alpha", 0.60)
        self.rate_filter_alpha = self.numeric_parameter("rate_filter_alpha", 0.40)
        self.command_sign = self.numeric_parameter("command_sign", 1.0)
        self.publish_debug = bool(self.get_parameter("publish_debug").value)

        self.tilt = 0.0
        self.tilt_rate = 0.0
        self.base_position = 0.0
        self.base_velocity = 0.0
        self.last_wheel_speed = 0.0
        self.last_time = self.get_clock().now()
        self.imu_initialized = False

        self.left_pub = self.create_publisher(Float64, "/tumbller/left_wheel/velocity_cmd", 10)
        self.right_pub = self.create_publisher(Float64, "/tumbller/right_wheel/velocity_cmd", 10)
        self.tilt_pub = self.create_publisher(Float64, "/tumbller/debug/tilt_rad", 10)
        self.cmd_pub = self.create_publisher(Float64, "/tumbller/debug/wheel_cmd_rad_s", 10)
        self.accel_pub = self.create_publisher(Float64, "/tumbller/debug/base_accel_m_s2", 10)
        self.base_position_pub = self.create_publisher(Float64, "/tumbller/debug/base_position_m", 10)
        self.create_subscription(Imu, "/tumbller/imu", self.on_imu, 20)

        self.create_timer(1.0 / self.control_rate_hz, self.on_timer)
        self.get_logger().info(
            "Controller Balance acceleration PID ready: "
            f"r={self.wheel_radius:.3f} m, ka={self.tilt_accel_gain:.2f}, "
            f"kwa={self.tilt_rate_accel_gain:.2f}, kx={self.position_kp:.2f}, "
            f"kv={self.velocity_kd:.2f}, upright_kx={self.upright_position_kp:.2f}, "
            f"upright_kv={self.upright_velocity_kd:.2f}, max_target={self.max_position_tilt:.2f}, max_a={self.max_base_accel:.2f}, "
            f"sign={self.command_sign}"
        )

    def numeric_parameter(self, name: str, default: float) -> float:
        param = self.get_parameter(name)
        if param.type_ == ParameterType.PARAMETER_NOT_SET:
            return default
        return float(param.value)

    def reset_controller_state(self, now) -> None:
        self.tilt = 0.0
        self.tilt_rate = 0.0
        self.base_position = 0.0
        self.base_velocity = 0.0
        self.last_wheel_speed = 0.0
        self.imu_initialized = False
        self.last_time = now
        self.publish_wheel_speed(0.0)
        self.get_logger().info("Simulation reset detected; controller state cleared.")

    def on_imu(self, msg: Imu) -> None:
        q = msg.orientation
        raw_tilt = pitch_from_quaternion(q.x, q.y, q.z, q.w)
        raw_rate = msg.angular_velocity.y

        if not self.imu_initialized:
            self.tilt = raw_tilt
            self.tilt_rate = raw_rate
            self.imu_initialized = True
            return

        self.tilt = self.pitch_filter_alpha * raw_tilt + (1.0 - self.pitch_filter_alpha) * self.tilt
        self.tilt_rate = self.rate_filter_alpha * raw_rate + (1.0 - self.rate_filter_alpha) * self.tilt_rate

    def desired_base_accel(self, tilt: float, tilt_rate: float) -> float:
        if abs(tilt) < self.upright_tilt_window and abs(tilt_rate) < self.upright_rate_window:
            target_tilt = self.upright_position_kp * self.base_position
            target_tilt += self.upright_velocity_kd * self.base_velocity
        else:
            target_tilt = self.position_kp * self.base_position
            target_tilt += self.velocity_kd * self.base_velocity

        target_tilt = clamp(target_tilt, -self.max_position_tilt, self.max_position_tilt)
        tilt_error = tilt - target_tilt
        balance_accel = self.tilt_accel_gain * tilt_error + self.tilt_rate_accel_gain * tilt_rate
        return clamp(balance_accel, -self.max_base_accel, self.max_base_accel)

    def slew_limit(self, target: float, dt: float) -> float:
        max_delta = self.max_wheel_accel * dt
        delta = clamp(target - self.last_wheel_speed, -max_delta, max_delta)
        self.last_wheel_speed += delta
        return self.last_wheel_speed

    def on_timer(self) -> None:
        now = self.get_clock().now()
        elapsed_ns = (now - self.last_time).nanoseconds

        if elapsed_ns < 0:
            self.reset_controller_state(now)
            return

        dt = max(elapsed_ns * 1e-9, 1e-4)
        self.last_time = now

        if abs(self.tilt) > self.max_tilt:
            self.base_velocity = 0.0
            self.last_wheel_speed = 0.0
            self.publish_wheel_speed(0.0)
            if self.publish_debug:
                self.publish_debug_value(self.cmd_pub, 0.0)
                self.publish_debug_value(self.accel_pub, 0.0)
            self.get_logger().warn(
                f"Tilt {self.tilt:.3f} rad exceeds safety limit {self.max_tilt:.3f}; stopping wheels.",
                throttle_duration_sec=1.0,
            )
            return

        tilt = 0.0 if abs(self.tilt) < self.deadband else self.tilt
        tilt_rate = 0.0 if abs(self.tilt_rate) < self.rate_deadband else self.tilt_rate

        base_accel = self.desired_base_accel(tilt, tilt_rate)
        self.base_velocity = clamp(
            self.base_velocity + base_accel * dt,
            -self.max_base_velocity,
            self.max_base_velocity,
        )
        self.base_position += self.base_velocity * dt

        target_wheel_speed = self.command_sign * self.base_velocity / self.wheel_radius
        target_wheel_speed = clamp(target_wheel_speed, -self.max_wheel_speed, self.max_wheel_speed)
        wheel_speed = self.slew_limit(target_wheel_speed, dt)
        self.publish_wheel_speed(wheel_speed)

        if self.publish_debug:
            self.publish_debug_value(self.tilt_pub, self.tilt)
            self.publish_debug_value(self.cmd_pub, wheel_speed)
            self.publish_debug_value(self.accel_pub, base_accel)
            self.publish_debug_value(self.base_position_pub, self.base_position)

    def publish_debug_value(self, publisher, value: float) -> None:
        msg = Float64()
        msg.data = value
        publisher.publish(msg)

    def publish_wheel_speed(self, speed: float) -> None:
        msg = Float64()
        msg.data = speed
        self.left_pub.publish(msg)
        self.right_pub.publish(msg)


def main() -> None:
    rclpy.init()
    node = BalanceController()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()