#!/usr/bin/env python3
"""2D self-balancing robot simulation: fixed PID vs AI-assisted PID.

The model is a simplified two-wheel inverted pendulum in the sagittal plane.
It intentionally avoids ROS/Gazebo dependencies so students can run quick
controller experiments before moving to the 3D simulator.
"""

from __future__ import annotations

import argparse
import csv
import html
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable


@dataclass
class Robot2DParams:
    gravity: float = 9.81
    com_height_m: float = 0.105
    wheel_radius_m: float = 0.034
    angular_damping: float = 0.08
    base_drag: float = 0.05
    max_accel_m_s2: float = 8.0
    max_speed_m_s: float = 1.2
    max_motor_rpm: float = 240.0
    fall_angle_rad: float = math.radians(45.0)


@dataclass
class FixedPidParams:
    kp: float = 13.5
    ki: float = 0.25
    kd: float = 2.25
    position_kp: float = 0.18
    velocity_kd: float = 0.35
    integral_limit: float = 0.40


@dataclass
class SimulationParams:
    dt: float = 0.005
    duration_s: float = 12.0
    initial_tilt_deg: float = 7.0
    impulse_time_s: float = 4.0
    impulse_duration_s: float = 0.12
    impulse_accel_m_s2: float = -2.5


@dataclass
class State:
    t: float
    theta: float
    theta_dot: float
    x: float
    x_dot: float


@dataclass
class ControllerOutput:
    accel: float
    rpm: float
    kp: float
    ki: float
    kd: float
    expert_balance: float
    expert_recovery: float
    expert_drift: float
    target_tilt: float


@dataclass
class SimResult:
    name: str
    rows: list[dict[str, float | str]]
    fallen: bool
    fall_time_s: float | None
    ise: float
    iae: float
    max_abs_tilt_deg: float
    max_abs_x_m: float
    max_abs_rpm: float
    settling_time_s: float | None


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def smoothstep(edge0: float, edge1: float, value: float) -> float:
    if edge0 == edge1:
        return 1.0 if value >= edge1 else 0.0
    x = clamp((value - edge0) / (edge1 - edge0), 0.0, 1.0)
    return x * x * (3.0 - 2.0 * x)


class FixedPidController:
    def __init__(self, params: FixedPidParams, robot: Robot2DParams) -> None:
        self.params = params
        self.robot = robot
        self.integral = 0.0

    def reset(self) -> None:
        self.integral = 0.0

    def step(self, state: State, dt: float) -> ControllerOutput:
        target_tilt = clamp(
            -(self.params.position_kp * state.x + self.params.velocity_kd * state.x_dot),
            -math.radians(10.0),
            math.radians(10.0),
        )
        error = state.theta - target_tilt
        self.integral = clamp(
            self.integral + error * dt,
            -self.params.integral_limit,
            self.params.integral_limit,
        )
        accel = (
            self.params.kp * error
            + self.params.ki * self.integral
            + self.params.kd * state.theta_dot
        )
        accel = clamp(accel, -self.robot.max_accel_m_s2, self.robot.max_accel_m_s2)
        rpm = accel_to_limited_rpm(accel, self.robot)
        return ControllerOutput(
            accel=accel,
            rpm=rpm,
            kp=self.params.kp,
            ki=self.params.ki,
            kd=self.params.kd,
            expert_balance=1.0,
            expert_recovery=0.0,
            expert_drift=0.0,
            target_tilt=target_tilt,
        )


class AiAssistedPidController:
    """Small mixture-of-experts gain scheduler around a PID core.

    This is a transparent baseline for an IA-enhanced PID: three expert gain
    sets are blended from the current angle, angular speed, and position drift.
    Later, the same interface can be replaced by a neural network, fuzzy system,
    or trained policy.
    """

    def __init__(self, robot: Robot2DParams) -> None:
        self.robot = robot
        self.integral = 0.0
        self.integral_limit = 0.28

        self.balance = FixedPidParams(kp=12.5, ki=0.20, kd=2.10, position_kp=0.16, velocity_kd=0.32)
        self.recovery = FixedPidParams(kp=20.0, ki=0.04, kd=4.20, position_kp=0.06, velocity_kd=0.18)
        self.drift = FixedPidParams(kp=10.5, ki=0.12, kd=2.50, position_kp=0.42, velocity_kd=0.80)

    def reset(self) -> None:
        self.integral = 0.0

    def step(self, state: State, dt: float) -> ControllerOutput:
        angle_score = smoothstep(math.radians(5.0), math.radians(18.0), abs(state.theta))
        rate_score = smoothstep(math.radians(25.0), math.radians(130.0), abs(state.theta_dot))
        drift_score = smoothstep(0.06, 0.45, abs(state.x))

        recovery_w = clamp(0.65 * angle_score + 0.35 * rate_score, 0.0, 1.0)
        drift_w = (1.0 - recovery_w) * drift_score
        balance_w = max(0.0, 1.0 - recovery_w - drift_w)
        total = balance_w + recovery_w + drift_w
        balance_w /= total
        recovery_w /= total
        drift_w /= total

        kp = blend(balance_w, self.balance.kp, recovery_w, self.recovery.kp, drift_w, self.drift.kp)
        ki = blend(balance_w, self.balance.ki, recovery_w, self.recovery.ki, drift_w, self.drift.ki)
        kd = blend(balance_w, self.balance.kd, recovery_w, self.recovery.kd, drift_w, self.drift.kd)
        position_kp = blend(
            balance_w,
            self.balance.position_kp,
            recovery_w,
            self.recovery.position_kp,
            drift_w,
            self.drift.position_kp,
        )
        velocity_kd = blend(
            balance_w,
            self.balance.velocity_kd,
            recovery_w,
            self.recovery.velocity_kd,
            drift_w,
            self.drift.velocity_kd,
        )

        target_tilt = clamp(
            -(position_kp * state.x + velocity_kd * state.x_dot),
            -math.radians(12.0),
            math.radians(12.0),
        )
        error = state.theta - target_tilt
        self.integral = clamp(self.integral + error * dt, -self.integral_limit, self.integral_limit)

        accel = kp * error + ki * self.integral + kd * state.theta_dot
        accel = clamp(accel, -self.robot.max_accel_m_s2, self.robot.max_accel_m_s2)
        rpm = accel_to_limited_rpm(accel, self.robot)
        return ControllerOutput(
            accel=accel,
            rpm=rpm,
            kp=kp,
            ki=ki,
            kd=kd,
            expert_balance=balance_w,
            expert_recovery=recovery_w,
            expert_drift=drift_w,
            target_tilt=target_tilt,
        )


def blend(w1: float, v1: float, w2: float, v2: float, w3: float, v3: float) -> float:
    return w1 * v1 + w2 * v2 + w3 * v3


def accel_to_limited_rpm(accel: float, robot: Robot2DParams) -> float:
    # Approximate wheel speed demand generated by base acceleration over 100 ms.
    wheel_rad_s = accel * 0.10 / robot.wheel_radius_m
    rpm = wheel_rad_s * 60.0 / (2.0 * math.pi)
    return clamp(rpm, -robot.max_motor_rpm, robot.max_motor_rpm)


def external_impulse(t: float, sim: SimulationParams) -> float:
    start = sim.impulse_time_s
    end = sim.impulse_time_s + sim.impulse_duration_s
    return sim.impulse_accel_m_s2 if start <= t < end else 0.0


def dynamics(state: State, commanded_accel: float, sim: SimulationParams, robot: Robot2DParams) -> tuple[float, float]:
    disturbance = external_impulse(state.t, sim)
    base_accel = commanded_accel + disturbance - robot.base_drag * state.x_dot
    theta_ddot = (
        robot.gravity / robot.com_height_m * math.sin(state.theta)
        - base_accel / robot.com_height_m * math.cos(state.theta)
        - robot.angular_damping * state.theta_dot
    )
    return theta_ddot, base_accel


def integrate(state: State, accel: float, sim: SimulationParams, robot: Robot2DParams) -> State:
    dt = sim.dt

    def deriv(s: State) -> tuple[float, float, float, float]:
        theta_ddot, base_accel = dynamics(s, accel, sim, robot)
        return s.theta_dot, theta_ddot, s.x_dot, base_accel

    k1 = deriv(state)
    s2 = State(
        state.t + dt * 0.5,
        state.theta + k1[0] * dt * 0.5,
        state.theta_dot + k1[1] * dt * 0.5,
        state.x + k1[2] * dt * 0.5,
        state.x_dot + k1[3] * dt * 0.5,
    )
    k2 = deriv(s2)
    s3 = State(
        state.t + dt * 0.5,
        state.theta + k2[0] * dt * 0.5,
        state.theta_dot + k2[1] * dt * 0.5,
        state.x + k2[2] * dt * 0.5,
        state.x_dot + k2[3] * dt * 0.5,
    )
    k3 = deriv(s3)
    s4 = State(
        state.t + dt,
        state.theta + k3[0] * dt,
        state.theta_dot + k3[1] * dt,
        state.x + k3[2] * dt,
        state.x_dot + k3[3] * dt,
    )
    k4 = deriv(s4)

    theta = state.theta + dt / 6.0 * (k1[0] + 2.0 * k2[0] + 2.0 * k3[0] + k4[0])
    theta_dot = state.theta_dot + dt / 6.0 * (k1[1] + 2.0 * k2[1] + 2.0 * k3[1] + k4[1])
    x = state.x + dt / 6.0 * (k1[2] + 2.0 * k2[2] + 2.0 * k3[2] + k4[2])
    x_dot = state.x_dot + dt / 6.0 * (k1[3] + 2.0 * k2[3] + 2.0 * k3[3] + k4[3])
    x_dot = clamp(x_dot, -robot.max_speed_m_s, robot.max_speed_m_s)
    return State(state.t + dt, theta, theta_dot, x, x_dot)


def simulate(
    name: str,
    controller_factory: Callable[[], FixedPidController | AiAssistedPidController],
    sim: SimulationParams,
    robot: Robot2DParams,
) -> SimResult:
    controller = controller_factory()
    controller.reset()
    state = State(0.0, math.radians(sim.initial_tilt_deg), 0.0, 0.0, 0.0)
    rows: list[dict[str, float | str]] = []
    fallen = False
    fall_time: float | None = None
    ise = 0.0
    iae = 0.0

    steps = int(sim.duration_s / sim.dt)
    for _ in range(steps + 1):
        output = controller.step(state, sim.dt)
        tilt_deg = math.degrees(state.theta)
        target_tilt_deg = math.degrees(output.target_tilt)
        theta_rate_deg_s = math.degrees(state.theta_dot)
        rows.append(
            {
                "controller": name,
                "time_s": state.t,
                "tilt_rad": state.theta,
                "tilt_deg": tilt_deg,
                "tilt_rate_rad_s": state.theta_dot,
                "tilt_rate_deg_s": theta_rate_deg_s,
                "x_m": state.x,
                "x_dot_m_s": state.x_dot,
                "command_accel_m_s2": output.accel,
                "command_motor_rpm": output.rpm,
                "target_tilt_deg": target_tilt_deg,
                "kp": output.kp,
                "ki": output.ki,
                "kd": output.kd,
                "expert_balance": output.expert_balance,
                "expert_recovery": output.expert_recovery,
                "expert_drift": output.expert_drift,
            }
        )
        ise += state.theta * state.theta * sim.dt
        iae += abs(state.theta) * sim.dt
        if abs(state.theta) >= robot.fall_angle_rad:
            fallen = True
            fall_time = state.t
            break
        state = integrate(state, output.accel, sim, robot)

    return SimResult(
        name=name,
        rows=rows,
        fallen=fallen,
        fall_time_s=fall_time,
        ise=ise,
        iae=iae,
        max_abs_tilt_deg=max(abs(float(row["tilt_deg"])) for row in rows),
        max_abs_x_m=max(abs(float(row["x_m"])) for row in rows),
        max_abs_rpm=max(abs(float(row["command_motor_rpm"])) for row in rows),
        settling_time_s=settling_time(rows),
    )


def settling_time(rows: list[dict[str, float | str]], band_deg: float = 1.0, window_s: float = 0.75) -> float | None:
    if not rows:
        return None
    dt = float(rows[1]["time_s"]) - float(rows[0]["time_s"]) if len(rows) > 1 else 0.005
    window = max(1, int(window_s / dt))
    abs_tilts = [abs(float(row["tilt_deg"])) for row in rows]
    for idx in range(0, max(0, len(rows) - window)):
        if max(abs_tilts[idx : idx + window]) <= band_deg:
            return float(rows[idx]["time_s"])
    return None


def write_csv(path: Path, results: Iterable[SimResult]) -> None:
    rows = [row for result in results for row in result.rows]
    fieldnames = list(rows[0].keys()) if rows else []
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def polyline(rows: list[dict[str, float | str]], x_key: str, y_key: str, box: tuple[int, int, int, int], x_max: float, y_min: float, y_max: float) -> str:
    left, top, width, height = box
    points: list[str] = []
    denom_y = y_max - y_min if y_max != y_min else 1.0
    for row in rows:
        x = float(row[x_key])
        y = float(row[y_key])
        sx = left + width * (x / x_max if x_max else 0.0)
        sy = top + height * (1.0 - (y - y_min) / denom_y)
        points.append(f"{sx:.2f},{sy:.2f}")
    return " ".join(points)


def render_chart(title: str, key: str, unit: str, results: list[SimResult], y_pad: float = 0.08) -> str:
    values = [float(row[key]) for result in results for row in result.rows]
    x_max = max(float(row["time_s"]) for result in results for row in result.rows)
    y_min = min(values)
    y_max = max(values)
    if abs(y_max - y_min) < 1e-9:
        y_min -= 1.0
        y_max += 1.0
    pad = max((y_max - y_min) * y_pad, 0.1)
    y_min -= pad
    y_max += pad
    box = (64, 24, 820, 240)
    zero_y = None
    if y_min < 0.0 < y_max:
        zero_y = box[1] + box[3] * (1.0 - (0.0 - y_min) / (y_max - y_min))

    colors = {"PID normal": "#1f77b4", "PID IA": "#d62728"}
    lines = []
    for result in results:
        pts = polyline(result.rows, "time_s", key, box, x_max, y_min, y_max)
        lines.append(
            f'<polyline points="{pts}" fill="none" stroke="{colors[result.name]}" stroke-width="2.3" stroke-linejoin="round" stroke-linecap="round" />'
        )
    zero_line = ""
    if zero_y is not None:
        zero_line = f'<line x1="64" x2="884" y1="{zero_y:.2f}" y2="{zero_y:.2f}" stroke="#8a8f98" stroke-dasharray="5 5" />'
    return f"""
<section class="chart">
  <h2>{html.escape(title)}</h2>
  <svg viewBox="0 0 920 310" role="img" aria-label="{html.escape(title)}">
    <rect x="64" y="24" width="820" height="240" fill="#ffffff" stroke="#d6d9de" />
    {zero_line}
    <line x1="64" x2="884" y1="264" y2="264" stroke="#4b5563" />
    <line x1="64" x2="64" y1="24" y2="264" stroke="#4b5563" />
    <text x="64" y="292" font-size="12">0 s</text>
    <text x="835" y="292" font-size="12">{x_max:.1f} s</text>
    <text x="8" y="32" font-size="12">{y_max:.2f} {html.escape(unit)}</text>
    <text x="8" y="264" font-size="12">{y_min:.2f} {html.escape(unit)}</text>
    {''.join(lines)}
  </svg>
</section>
"""


def write_html(path: Path, results: list[SimResult], sim: SimulationParams, robot: Robot2DParams, csv_name: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    cards = []
    for result in results:
        fall_text = f"cae en {result.fall_time_s:.2f} s" if result.fallen and result.fall_time_s is not None else "no cae"
        settle_text = f"{result.settling_time_s:.2f} s" if result.settling_time_s is not None else "no estabiliza < 1 deg"
        cards.append(
            f"""
      <article class="card">
        <h2>{html.escape(result.name)}</h2>
        <dl>
          <div><dt>Estado</dt><dd>{fall_text}</dd></div>
          <div><dt>Max tilt</dt><dd>{result.max_abs_tilt_deg:.2f} deg</dd></div>
          <div><dt>Settling</dt><dd>{settle_text}</dd></div>
          <div><dt>IAE</dt><dd>{result.iae:.4f}</dd></div>
          <div><dt>Max x</dt><dd>{result.max_abs_x_m:.3f} m</dd></div>
          <div><dt>Max RPM</dt><dd>{result.max_abs_rpm:.1f}</dd></div>
        </dl>
      </article>
"""
        )

    charts = [
        render_chart("Inclinacion del robot", "tilt_deg", "deg", results),
        render_chart("Comando de aceleracion de la base", "command_accel_m_s2", "m/s^2", results),
        render_chart("Deriva de posicion", "x_m", "m", results),
        render_chart("RPM equivalente del motor", "command_motor_rpm", "rpm", results),
        render_chart("Ganancia Kp adaptativa", "kp", "", results),
        render_chart("Peso del experto de recuperacion", "expert_recovery", "", results),
    ]
    html_doc = f"""<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Simulacion 2D PID vs PID IA</title>
  <style>
    :root {{ color-scheme: light; font-family: Arial, Helvetica, sans-serif; }}
    body {{ margin: 0; background: #f4f6f8; color: #17202a; }}
    header {{ padding: 28px 36px 16px; background: #ffffff; border-bottom: 1px solid #d9dde3; }}
    h1 {{ margin: 0 0 8px; font-size: 28px; letter-spacing: 0; }}
    p {{ max-width: 940px; line-height: 1.45; }}
    main {{ padding: 24px 36px 40px; }}
    .cards {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 14px; max-width: 980px; }}
    .card {{ background: #fff; border: 1px solid #d9dde3; border-radius: 8px; padding: 16px; }}
    .card h2 {{ margin: 0 0 10px; font-size: 18px; }}
    dl {{ margin: 0; display: grid; gap: 8px; }}
    dl div {{ display: flex; justify-content: space-between; gap: 16px; }}
    dt {{ color: #5f6b7a; }}
    dd {{ margin: 0; font-weight: 700; text-align: right; }}
    .legend {{ display: flex; gap: 18px; align-items: center; margin: 20px 0 12px; }}
    .legend span {{ display: inline-flex; align-items: center; gap: 6px; font-weight: 700; }}
    .swatch {{ width: 28px; height: 4px; display: inline-block; border-radius: 2px; }}
    .blue {{ background: #1f77b4; }}
    .red {{ background: #d62728; }}
    .chart {{ max-width: 980px; margin: 18px 0; background: #fff; border: 1px solid #d9dde3; border-radius: 8px; padding: 14px 16px; }}
    .chart h2 {{ margin: 0 0 8px; font-size: 18px; }}
    svg {{ width: 100%; height: auto; }}
    code {{ background: #e9edf2; padding: 2px 5px; border-radius: 4px; }}
  </style>
</head>
<body>
  <header>
    <h1>Simulacion 2D: PID normal vs PID potenciado por IA</h1>
    <p>Modelo simplificado de robot auto-balanceado como pendulo invertido sobre ruedas. La perturbacion inicia en {sim.initial_tilt_deg:.1f} deg y aplica un empuje de {sim.impulse_accel_m_s2:.1f} m/s^2 durante {sim.impulse_duration_s:.2f} s en t={sim.impulse_time_s:.1f} s. CSV: <code>{html.escape(csv_name)}</code>.</p>
  </header>
  <main>
    <section class="cards">
      {''.join(cards)}
    </section>
    <div class="legend">
      <span><i class="swatch blue"></i>PID normal</span>
      <span><i class="swatch red"></i>PID IA</span>
    </div>
    {''.join(charts)}
    <p>Parametros fisicos: L={robot.com_height_m:.3f} m, radio rueda={robot.wheel_radius_m:.3f} m, aceleracion maxima={robot.max_accel_m_s2:.1f} m/s^2.</p>
  </main>
</body>
</html>
"""
    path.write_text(html_doc, encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Simulacion 2D PID vs PID potenciado por IA para robot auto-balanceado.")
    parser.add_argument("--duration", type=float, default=12.0, help="Duracion de simulacion en segundos.")
    parser.add_argument("--dt", type=float, default=0.005, help="Paso de integracion en segundos.")
    parser.add_argument("--initial-tilt-deg", type=float, default=7.0, help="Inclinacion inicial desde vertical.")
    parser.add_argument("--impulse-time", type=float, default=4.0, help="Tiempo donde se aplica una perturbacion.")
    parser.add_argument("--impulse-accel", type=float, default=-2.5, help="Aceleracion externa de perturbacion.")
    parser.add_argument("--output-dir", type=Path, default=Path("data") / "sim_2d", help="Carpeta de salida.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    robot = Robot2DParams()
    sim = SimulationParams(
        dt=args.dt,
        duration_s=args.duration,
        initial_tilt_deg=args.initial_tilt_deg,
        impulse_time_s=args.impulse_time,
        impulse_accel_m_s2=args.impulse_accel,
    )
    fixed_params = FixedPidParams()
    results = [
        simulate("PID normal", lambda: FixedPidController(fixed_params, robot), sim, robot),
        simulate("PID IA", lambda: AiAssistedPidController(robot), sim, robot),
    ]

    args.output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = args.output_dir / "pid_vs_pid_ai_2d.csv"
    html_path = args.output_dir / "pid_vs_pid_ai_2d.html"
    write_csv(csv_path, results)
    write_html(html_path, results, sim, robot, csv_path.name)

    print("Simulacion 2D terminada")
    for result in results:
        status = f"cae en {result.fall_time_s:.2f}s" if result.fallen and result.fall_time_s is not None else "no cae"
        settling = f"{result.settling_time_s:.2f}s" if result.settling_time_s is not None else "sin settling <1deg"
        print(
            f"- {result.name}: {status}, max_tilt={result.max_abs_tilt_deg:.2f}deg, "
            f"IAE={result.iae:.4f}, settling={settling}, max_rpm={result.max_abs_rpm:.1f}"
        )
    print(f"CSV: {csv_path}")
    print(f"HTML: {html_path}")


if __name__ == "__main__":
    main()


