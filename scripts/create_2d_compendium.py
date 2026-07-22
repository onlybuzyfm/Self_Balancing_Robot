#!/usr/bin/env python3
"""Build one self-contained educational HTML compendium for the 2D PID simulation."""

from __future__ import annotations

import argparse
import csv
import html
import json
import math
from pathlib import Path


STYLE = """
:root { font-family: Arial, Helvetica, sans-serif; color-scheme: light; }
* { box-sizing: border-box; }
body { margin: 0; background: #f3f6f8; color: #17202a; }
header { background: #ffffff; border-bottom: 1px solid #d7dde5; padding: 26px 34px 18px; position: sticky; top: 0; z-index: 10; }
h1 { margin: 0 0 8px; font-size: 28px; letter-spacing: 0; }
header p { margin: 0; color: #465463; max-width: 1040px; line-height: 1.45; }
nav { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 16px; }
nav a { color: #17202a; text-decoration: none; border: 1px solid #b7c0ca; background: #fff; padding: 7px 10px; border-radius: 6px; font-weight: 700; font-size: 14px; }
nav a:hover { background: #edf1f5; }
main { padding: 24px 34px 42px; max-width: 1180px; }
section { margin: 0 0 24px; }
.panel { background: #fff; border: 1px solid #d7dde5; border-radius: 8px; padding: 18px; }
h2 { margin: 0 0 12px; font-size: 22px; }
h3 { margin: 18px 0 8px; font-size: 17px; }
p, li { line-height: 1.5; }
.text-note { margin: -4px 0 8px; color: #536171; font-size: 13px; }
.grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(230px, 1fr)); gap: 12px; }
.metric { background: #fff; border: 1px solid #d7dde5; border-radius: 8px; padding: 14px; }
.metric strong { color: #536171; display: block; font-size: 13px; margin-bottom: 6px; }
.metric b { font-size: 24px; display: block; }
.metric small { color: #536171; display: block; margin-top: 5px; line-height: 1.35; }
.good b { color: #16803c; }
.tradeoff b { color: #9a5b00; }
canvas { width: 100%; height: auto; display: block; background: #eef2f5; border: 1px solid #ccd2da; border-radius: 6px; }
.controls { display: grid; grid-template-columns: auto auto minmax(220px, 1fr) auto; gap: 12px; align-items: center; margin-top: 12px; }
button, select { height: 36px; border: 1px solid #aeb7c2; background: #fff; border-radius: 6px; padding: 0 12px; font-weight: 700; cursor: pointer; }
button:hover, select:hover { background: #f0f3f6; }
input[type=range] { width: 100%; }
.legend { display: flex; gap: 20px; flex-wrap: wrap; margin: 12px 0 0; color: #3f4c5a; }
.legend span { display: inline-flex; align-items: center; gap: 7px; font-weight: 700; }
.swatch { width: 28px; height: 5px; border-radius: 3px; display: inline-block; }
.blue { background: #1f77b4; }
.red { background: #d62728; }
.readout { font-variant-numeric: tabular-nums; font-weight: 700; margin-left: auto; }
.table-wrap { overflow-x: auto; }
table { border-collapse: collapse; width: 100%; min-width: 680px; }
th, td { border: 1px solid #d7dde5; padding: 9px 10px; text-align: left; }
th { background: #edf1f5; }
code, pre { background: #e9edf2; border-radius: 5px; }
code { padding: 2px 5px; }
pre { padding: 12px; overflow-x: auto; }
.callout { border-left: 4px solid #1f77b4; background: #eef6fc; padding: 12px 14px; border-radius: 6px; }
.two-col { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 14px; }
.chart { margin-top: 12px; }
svg { width: 100%; height: auto; background: #fff; border: 1px solid #d7dde5; border-radius: 6px; }
footer { color: #536171; border-top: 1px solid #d7dde5; padding: 16px 34px 30px; }
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create one HTML guide + animation compendium.")
    parser.add_argument("--csv", type=Path, default=Path("data") / "sim_2d" / "pid_vs_pid_ai_2d.csv")
    parser.add_argument("--output", type=Path, default=Path("data") / "sim_2d" / "guia_compendio_pid_ia_2d.html")
    parser.add_argument("--stride", type=int, default=8)
    return parser.parse_args()


def load_csv(path: Path) -> dict[str, list[dict[str, float]]]:
    grouped: dict[str, list[dict[str, float]]] = {}
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = row["controller"]
            grouped.setdefault(name, []).append(
                {
                    "t": float(row["time_s"]),
                    "tilt": float(row["tilt_rad"]),
                    "tiltDeg": float(row["tilt_deg"]),
                    "rateDeg": float(row["tilt_rate_deg_s"]),
                    "x": float(row["x_m"]),
                    "abs_x": abs(float(row["x_m"])),
                    "v": float(row["x_dot_m_s"]),
                    "accel": float(row["command_accel_m_s2"]),
                    "rpm": float(row["command_motor_rpm"]),
                    "kp": float(row["kp"]),
                    "ki": float(row["ki"]),
                    "kd": float(row["kd"]),
                    "balance": float(row["expert_balance"]),
                    "recovery": float(row["expert_recovery"]),
                    "drift": float(row["expert_drift"]),
                }
            )
    for required in ("PID normal", "PID IA"):
        if required not in grouped:
            raise ValueError(f"CSV missing controller {required}")
    return grouped


def downsample(data: dict[str, list[dict[str, float]]], stride: int) -> dict[str, list[dict[str, float]]]:
    step = max(1, stride)
    return {name: rows[::step] for name, rows in data.items()}


def summarize(rows: list[dict[str, float]]) -> dict[str, float | None]:
    max_tilt = max(abs(r["tiltDeg"]) for r in rows)
    max_rpm = max(abs(r["rpm"]) for r in rows)
    max_x = max(abs(r["x"]) for r in rows)
    iae = 0.0
    ise = 0.0
    settling = None
    for idx, row in enumerate(rows):
        if idx > 0:
            dt = row["t"] - rows[idx - 1]["t"]
            iae += abs(row["tilt"]) * dt
            ise += row["tilt"] * row["tilt"] * dt
    window = max(1, int(0.75 / max(rows[1]["t"] - rows[0]["t"], 1e-6))) if len(rows) > 1 else 1
    abs_tilts = [abs(r["tiltDeg"]) for r in rows]
    for idx in range(0, max(0, len(rows) - window)):
        if max(abs_tilts[idx : idx + window]) <= 1.0:
            settling = rows[idx]["t"]
            break
    final_abs_x = abs(rows[-1]["x"])
    return {"max_tilt": max_tilt, "max_rpm": max_rpm, "max_x": max_x, "final_abs_x": final_abs_x, "iae": iae, "ise": ise, "settling": settling}


def pct(base: float, value: float) -> float:
    return 0.0 if base == 0 else (base - value) / base * 100.0


def chart_svg(
    title: str,
    data: dict[str, list[dict[str, float]]],
    key: str,
    unit: str,
    impulse_time: float = 4.0,
    note: str | None = None,
) -> str:
    colors = {"PID normal": "#1f77b4", "PID IA": "#d62728"}
    all_rows = [row for rows in data.values() for row in rows]
    x_max = max(row["t"] for row in all_rows)
    ys = [row[key] for row in all_rows]
    y_min = min(ys)
    y_max = max(ys)
    if abs(y_max - y_min) < 1e-9:
        y_min -= 1.0
        y_max += 1.0
    pad = max((y_max - y_min) * 0.08, 0.1)
    y_min -= pad
    y_max += pad
    left, top, width, height = 64, 34, 830, 230

    def xy(row: dict[str, float]) -> tuple[float, float]:
        x = left + width * row["t"] / x_max
        y = top + height * (1 - (row[key] - y_min) / (y_max - y_min))
        return x, y

    def point(row: dict[str, float]) -> str:
        x, y = xy(row)
        return f"{x:.2f},{y:.2f}"

    lines = []
    final_labels = []
    for name in ("PID normal", "PID IA"):
        pts = " ".join(point(r) for r in data[name])
        final_x, final_y = xy(data[name][-1])
        final_value = data[name][-1][key]
        label_y = max(top + 12, min(top + height - 8, final_y))
        label = f"{name}: {final_value:.2f}{(' ' + unit) if unit else ''}"
        lines.append(f'<polyline points="{pts}" fill="none" stroke="{colors[name]}" stroke-width="2.3" stroke-linejoin="round" stroke-linecap="round" />')
        final_labels.append(f'<circle cx="{final_x:.2f}" cy="{final_y:.2f}" r="3.5" fill="{colors[name]}" />')
        final_labels.append(f'<text x="{min(final_x + 8, left + width - 145):.2f}" y="{label_y:.2f}" font-size="11" fill="{colors[name]}">{html.escape(label)}</text>')
    zero = ""
    if y_min < 0 < y_max:
        zy = top + height * (1 - (0 - y_min) / (y_max - y_min))
        zero = f'<line x1="{left}" y1="{zy:.2f}" x2="{left + width}" y2="{zy:.2f}" stroke="#8a8f98" stroke-dasharray="5 5" />'
    impulse_x = left + width * min(max(impulse_time, 0.0), x_max) / x_max
    impulse = (
        f'<line x1="{impulse_x:.2f}" y1="{top}" x2="{impulse_x:.2f}" y2="{top + height}" stroke="#8f5b00" stroke-width="1.6" stroke-dasharray="7 5" />'
        f'<text x="{min(impulse_x + 6, left + width - 115):.2f}" y="{top + 14}" font-size="11" fill="#8f5b00">perturbacion t={impulse_time:.1f}s</text>'
    )
    note_html = f'<p class="text-note">{html.escape(note)}</p>' if note else ""
    return f"""
<div class="chart">
  <h3>{html.escape(title)}</h3>
  {note_html}
  <svg viewBox="0 0 930 310" role="img" aria-label="{html.escape(title)} con perturbacion marcada">
    <rect x="{left}" y="{top}" width="{width}" height="{height}" fill="#ffffff" stroke="#d7dde5" />
    {zero}
    {impulse}
    <line x1="{left}" x2="{left + width}" y1="{top + height}" y2="{top + height}" stroke="#4b5563" />
    <line x1="{left}" x2="{left}" y1="{top}" y2="{top + height}" stroke="#4b5563" />
    <text x="{left}" y="292" font-size="12">0 s</text>
    <text x="850" y="292" font-size="12">{x_max:.1f} s</text>
    <text x="8" y="36" font-size="12">{y_max:.2f} {html.escape(unit)}</text>
    <text x="8" y="264" font-size="12">{y_min:.2f} {html.escape(unit)}</text>
    {''.join(lines)}
    {''.join(final_labels)}
  </svg>
</div>
"""


def build_html(data: dict[str, list[dict[str, float]]], anim_data: dict[str, list[dict[str, float]]]) -> str:
    normal = summarize(data["PID normal"])
    ai = summarize(data["PID IA"])
    peak_gain = pct(float(normal["max_tilt"]), float(ai["max_tilt"]))
    iae_gain = pct(float(normal["iae"]), float(ai["iae"]))
    rpm_cost = 0.0 if normal["max_rpm"] == 0 else (float(ai["max_rpm"]) - float(normal["max_rpm"])) / float(normal["max_rpm"]) * 100.0
    final_drift_gain = pct(float(normal["final_abs_x"]), float(ai["final_abs_x"]))
    charts = "".join(
        [
            chart_svg("Inclinacion del cuerpo", data, "tiltDeg", "deg", note="La linea vertical marca el golpe externo; despues se compara que controlador vuelve mas cerca de cero."),
            chart_svg("Comando equivalente de motor", data, "rpm", "rpm", note="Aqui se ve el costo de la mejora: el PID IA puede pedir mas motor para corregir antes."),
            chart_svg("Deriva horizontal", data, "x", "m", note="La curva muestra hacia donde se desplaza la base; el valor final permite ver si la deriva baja."),
            chart_svg("Magnitud de deriva |x|", data, "abs_x", "m", note="Esta grafica elimina el signo y muestra si la distancia al origen va bajando despues de la perturbacion."),
            chart_svg("Ganancia Kp usada", data, "kp", "", note="En el PID IA, Kp cambia porque la mezcla de expertos ajusta la agresividad del controlador."),
            chart_svg("Peso del experto de recuperacion", data, "recovery", "", note="Despues de la perturbacion deberia subir cuando el controlador detecta mayor riesgo de caida."),
        ]
    )
    js_data = json.dumps(anim_data, separators=(",", ":"))
    return f"""<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Guia compendio PID vs PID IA - Robot auto-balanceado</title>
  <style>{STYLE}</style>
</head>
<body>
<header>
  <h1>Guia compendio: PID normal vs PID potenciado por IA</h1>
  <p>Simulacion 2D educativa de un robot auto-balanceado de dos ruedas. Este documento junta la guia teorica, las metricas, la animacion y las actividades en un solo HTML.</p>
  <nav>
    <a href="#objetivo">Objetivo</a>
    <a href="#modelo">Modelo 2D</a>
    <a href="#control">Controladores</a>
    <a href="#resultados">Resultados</a>
    <a href="#animacion">Animacion</a>
    <a href="#graficas">Graficas</a>
    <a href="#actividades">Actividades</a>
  </nav>
</header>
<main>
  <section id="objetivo" class="panel">
    <h2>1. Objetivo de aprendizaje</h2>
    <p>Comprender como se estabiliza un robot auto-balanceado usando un controlador PID clasico y como una capa de inteligencia artificial puede ajustar sus ganancias para mejorar el desempeno.</p>
    <div class="callout"><strong>Idea central:</strong> el PID IA no reemplaza al PID. Lo potencia ajustando <code>Kp</code>, <code>Ki</code> y <code>Kd</code> segun el estado del robot.</div>
  </section>

  <section id="modelo" class="panel">
    <h2>2. Modelo 2D del robot</h2>
    <p>El robot se representa como un pendulo invertido sobre ruedas. La variable principal es <code>theta</code>, el angulo del cuerpo respecto a la vertical. Cuando <code>theta = 0</code>, el robot esta de pie.</p>
    <pre><code>theta_ddot = (g / L) * sin(theta) - (x_ddot / L) * cos(theta) - damping * theta_dot</code></pre>
    <p>Este modelo simplificado permite probar ideas de control antes de pasar a Gazebo 3D o al robot fisico.</p>
  </section>

  <section id="control" class="panel">
    <h2>3. Controladores comparados</h2>
    <div class="two-col">
      <article>
        <h3>PID normal</h3>
        <p>Usa ganancias fijas durante toda la simulacion:</p>
        <pre><code>u = Kp * error + Ki * integral(error) + Kd * derivative(error)</code></pre>
        <p>Es simple, explicable y muy bueno como linea base.</p>
      </article>
      <article>
        <h3>PID potenciado por IA</h3>
        <p>Usa una mezcla de expertos para cambiar ganancias segun la situacion:</p>
        <ul>
          <li><strong>Balance:</strong> movimientos suaves cerca de cero grados.</li>
          <li><strong>Recuperacion:</strong> accion fuerte cuando hay riesgo de caida.</li>
          <li><strong>Deriva:</strong> corrige desplazamiento horizontal acumulado.</li>
        </ul>
      </article>
    </div>
  </section>

  <section id="resultados">
    <h2>4. Resumen de resultados</h2>
    <div class="grid">
      <article class="metric good"><strong>Mejora visible 1</strong><b>{peak_gain:.1f}% menos pico</b><small>El PID IA alcanza menor inclinacion maxima: {ai['max_tilt']:.2f} deg vs {normal['max_tilt']:.2f} deg.</small></article>
      <article class="metric good"><strong>Mejora visible 2</strong><b>{iae_gain:.1f}% menos error</b><small>El error absoluto integrado baja de {normal['iae']:.4f} a {ai['iae']:.4f}.</small></article>
      <article class="metric tradeoff"><strong>Costo de la mejora</strong><b>{rpm_cost:+.1f}% RPM max</b><small>El PID IA usa mas esfuerzo: {ai['max_rpm']:.1f} rpm vs {normal['max_rpm']:.1f} rpm.</small></article>
      <article class="metric good"><strong>Deriva final</strong><b>{final_drift_gain:.1f}% menos |x| final</b><small>Al final queda mas cerca del origen: {ai['final_abs_x']:.3f} m vs {normal['final_abs_x']:.3f} m.</small></article>
    </div>
    <div class="panel" style="margin-top:12px;">
      <div class="table-wrap">
        <table>
          <thead><tr><th>Controlador</th><th>Max tilt</th><th>IAE</th><th>Max x</th><th>|x| final</th><th>Max RPM</th><th>Interpretacion</th></tr></thead>
          <tbody>
            <tr><td>PID normal</td><td>{normal['max_tilt']:.2f} deg</td><td>{normal['iae']:.4f}</td><td>{normal['max_x']:.3f} m</td><td>{normal['final_abs_x']:.3f} m</td><td>{normal['max_rpm']:.1f}</td><td>Base estable y sencilla.</td></tr>
            <tr><td>PID IA</td><td>{ai['max_tilt']:.2f} deg</td><td>{ai['iae']:.4f}</td><td>{ai['max_x']:.3f} m</td><td>{ai['final_abs_x']:.3f} m</td><td>{ai['max_rpm']:.1f}</td><td>Mejor estabilidad angular y menor deriva final con mas esfuerzo.</td></tr>
          </tbody>
        </table>
      </div>
    </div>
  </section>

  <section id="animacion" class="panel">
    <h2>5. Animacion de estabilizacion</h2>
    <canvas id="canvas" width="1080" height="560"></canvas>
    <div class="controls">
      <button id="play" type="button">Pausa</button>
      <button id="reset" type="button">Reset</button>
      <input id="slider" type="range" min="0" max="0" value="0" />
      <select id="speed" aria-label="Velocidad"><option value="0.5">0.5x</option><option value="1" selected>1x</option><option value="2">2x</option><option value="4">4x</option></select>
    </div>
    <div class="legend"><span><i class="swatch blue"></i>PID normal</span><span><i class="swatch red"></i>PID IA</span><span class="readout" id="time">t = 0.00 s</span></div>
  </section>

  <section id="graficas" class="panel">
    <h2>6. Graficas principales</h2>
    <div class="legend"><span><i class="swatch blue"></i>PID normal</span><span><i class="swatch red"></i>PID IA</span></div>
    {charts}
  </section>

  <section id="actividades" class="panel">
    <h2>7. Actividades para estudiantes</h2>
    <h3>Actividad 1: Observar la mejora</h3>
    <ol><li>Reproduce la animacion.</li><li>Compara cual cuerpo se aleja mas de la vertical.</li><li>Relaciona lo observado con la metrica de max tilt.</li></ol>
    <h3>Actividad 2: Cambiar condiciones iniciales</h3>
    <pre><code>python scripts/sim_2d_pid_ai.py --initial-tilt-deg 10
python scripts/create_2d_compendium.py</code></pre>
    <h3>Actividad 3: Aumentar perturbacion</h3>
    <pre><code>python scripts/sim_2d_pid_ai.py --impulse-accel -5.0
python scripts/create_2d_compendium.py</code></pre>
    <h3>Preguntas de reflexion</h3>
    <ul><li>Por que el PID IA puede mejorar el error pero usar mas RPM?</li><li>Que pasaria si el motor real no puede entregar esas RPM?</li><li>Cuando conviene preferir un controlador mas suave aunque tenga mas error?</li></ul>
  </section>
</main>
<footer>Generado desde <code>scripts/create_2d_compendium.py</code> usando <code>data/sim_2d/pid_vs_pid_ai_2d.csv</code>.</footer>
<script>
const DATA = {js_data};
const canvas = document.getElementById('canvas');
const ctx = canvas.getContext('2d');
const slider = document.getElementById('slider');
const playButton = document.getElementById('play');
const resetButton = document.getElementById('reset');
const speedSelect = document.getElementById('speed');
const timeLabel = document.getElementById('time');
let frame = 0;
let playing = true;
let lastTimestamp = performance.now();
const controllers = ['PID normal', 'PID IA'];
const totalFrames = Math.max(...controllers.map(name => DATA[name].length));
slider.max = String(totalFrames - 1);
function clamp(value, low, high) {{ return Math.max(low, Math.min(high, value)); }}
function rowAt(name, index) {{ const rows = DATA[name]; return rows[Math.min(index, rows.length - 1)]; }}
function drawGauge(x, y, w, label, value, maxValue, color) {{
  ctx.fillStyle = '#edf1f5'; ctx.fillRect(x, y, w, 10);
  const fill = clamp(Math.abs(value) / maxValue, 0, 1) * w;
  ctx.fillStyle = color; ctx.fillRect(x, y, fill, 10);
  ctx.fillStyle = '#34404d'; ctx.font = '13px Arial'; ctx.fillText(label + ': ' + value.toFixed(1), x, y - 6);
}}
function drawRobot(panel, row, color, title) {{
  const groundY = panel.y + panel.h - 88; const centerX = panel.x + panel.w / 2; const scaleX = 92;
  const wheelR = 24; const axleY = groundY - wheelR; const axleX = clamp(centerX + row.x * scaleX, panel.x + 58, panel.x + panel.w - 58);
  const theta = row.tilt;
  ctx.save(); ctx.fillStyle = '#ffffff'; ctx.strokeStyle = '#d2d8df'; ctx.lineWidth = 1; ctx.fillRect(panel.x, panel.y, panel.w, panel.h); ctx.strokeRect(panel.x, panel.y, panel.w, panel.h);
  ctx.fillStyle = '#1f2933'; ctx.font = 'bold 19px Arial'; ctx.fillText(title, panel.x + 18, panel.y + 30);
  ctx.font = '14px Arial'; ctx.fillStyle = '#536171'; ctx.fillText('tilt ' + row.tiltDeg.toFixed(2) + ' deg', panel.x + 18, panel.y + 55); ctx.fillText('x ' + row.x.toFixed(3) + ' m', panel.x + 18, panel.y + 76); ctx.fillText('rpm ' + row.rpm.toFixed(1), panel.x + 18, panel.y + 97); ctx.fillText('Kp ' + row.kp.toFixed(2), panel.x + panel.w - 112, panel.y + 55); ctx.fillText('rec IA ' + row.recovery.toFixed(2), panel.x + panel.w - 112, panel.y + 76);
  ctx.strokeStyle = '#9aa5b1'; ctx.lineWidth = 2; ctx.beginPath(); ctx.moveTo(panel.x + 26, groundY); ctx.lineTo(panel.x + panel.w - 26, groundY); ctx.stroke();
  ctx.strokeStyle = '#c2c8d0'; ctx.setLineDash([5,7]); ctx.beginPath(); ctx.moveTo(centerX, panel.y + 116); ctx.lineTo(centerX, groundY + 28); ctx.stroke(); ctx.setLineDash([]);
  ctx.save(); ctx.translate(axleX, axleY); ctx.rotate(-theta); ctx.fillStyle = color; ctx.strokeStyle = '#17202a'; ctx.lineWidth = 2; ctx.fillRect(-26, -148, 52, 140); ctx.strokeRect(-26, -148, 52, 140); ctx.fillStyle = 'rgba(255,255,255,0.38)'; ctx.fillRect(-18, -132, 36, 40); ctx.fillStyle = '#111827'; ctx.beginPath(); ctx.arc(0, -96, 5, 0, Math.PI * 2); ctx.fill(); ctx.restore();
  ctx.fillStyle = '#111827'; ctx.beginPath(); ctx.arc(axleX - 28, axleY, wheelR, 0, Math.PI * 2); ctx.fill(); ctx.beginPath(); ctx.arc(axleX + 28, axleY, wheelR, 0, Math.PI * 2); ctx.fill();
  ctx.strokeStyle = '#f8fafc'; ctx.lineWidth = 3; const spin = row.t * row.rpm * 0.035;
  for (const wx of [axleX - 28, axleX + 28]) {{ ctx.beginPath(); ctx.moveTo(wx, axleY); ctx.lineTo(wx + Math.cos(spin) * wheelR * 0.75, axleY + Math.sin(spin) * wheelR * 0.75); ctx.stroke(); }}
  drawGauge(panel.x + 18, panel.y + panel.h - 50, panel.w - 36, 'motor rpm', row.rpm, 240, color);
  drawGauge(panel.x + 18, panel.y + panel.h - 20, panel.w - 36, 'error deg', row.tiltDeg, 45, color);
  ctx.restore();
}}
function draw() {{
  ctx.clearRect(0, 0, canvas.width, canvas.height); ctx.fillStyle = '#eef2f5'; ctx.fillRect(0, 0, canvas.width, canvas.height);
  const normal = rowAt('PID normal', frame); const ai = rowAt('PID IA', frame);
  drawRobot({{x: 24, y: 22, w: 506, h: 500}}, normal, '#1f77b4', 'PID normal');
  drawRobot({{x: 550, y: 22, w: 506, h: 500}}, ai, '#d62728', 'PID potenciado por IA');
  timeLabel.textContent = 't = ' + Math.max(normal.t, ai.t).toFixed(2) + ' s'; slider.value = String(frame);
}}
function tick(timestamp) {{
  const dtMs = timestamp - lastTimestamp; const speed = Number(speedSelect.value);
  if (playing && dtMs > 42 / speed) {{ frame = (frame + 1) % totalFrames; lastTimestamp = timestamp; draw(); }}
  requestAnimationFrame(tick);
}}
playButton.addEventListener('click', () => {{ playing = !playing; playButton.textContent = playing ? 'Pausa' : 'Play'; }});
resetButton.addEventListener('click', () => {{ frame = 0; playing = false; playButton.textContent = 'Play'; draw(); }});
slider.addEventListener('input', () => {{ frame = Number(slider.value); playing = false; playButton.textContent = 'Play'; draw(); }});
draw(); requestAnimationFrame(tick);
</script>
</body>
</html>
"""


def main() -> None:
    args = parse_args()
    data = load_csv(args.csv)
    anim_data = downsample(data, args.stride)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(build_html(data, anim_data), encoding="utf-8")
    print(f"Compendium written: {args.output}")


if __name__ == "__main__":
    main()



