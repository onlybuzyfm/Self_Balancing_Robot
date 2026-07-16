#!/usr/bin/env python3
"""Create an educational 2D animation from the PID vs PID-AI CSV."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


HTML_TEMPLATE = """<!doctype html>
<html lang=\"es\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>Animacion 2D PID vs PID IA</title>
  <style>
    :root { font-family: Arial, Helvetica, sans-serif; color-scheme: light; }
    body { margin: 0; background: #f4f6f8; color: #17202a; }
    header { background: #fff; border-bottom: 1px solid #d9dde3; padding: 24px 30px 16px; }
    h1 { margin: 0 0 8px; font-size: 28px; letter-spacing: 0; }
    p { margin: 0; max-width: 960px; line-height: 1.45; color: #3f4c5a; }
    main { padding: 22px 30px 36px; }
    .stage { max-width: 1080px; background: #fff; border: 1px solid #d9dde3; border-radius: 8px; padding: 14px; }
    canvas { width: 100%; height: auto; display: block; background: #eef2f5; border: 1px solid #ccd2da; border-radius: 6px; }
    .controls { display: grid; grid-template-columns: auto auto minmax(220px, 1fr) auto; gap: 12px; align-items: center; margin-top: 14px; }
    button, select { height: 36px; border: 1px solid #aeb7c2; background: #fff; border-radius: 6px; padding: 0 12px; font-weight: 700; cursor: pointer; }
    button:hover, select:hover { background: #f0f3f6; }
    input[type=range] { width: 100%; }
    .readout { font-variant-numeric: tabular-nums; font-weight: 700; min-width: 92px; text-align: right; }
    .legend { display: flex; gap: 20px; flex-wrap: wrap; margin: 14px 0 0; color: #3f4c5a; }
    .metrics { max-width: 1080px; display: grid; grid-template-columns: repeat(auto-fit, minmax(210px, 1fr)); gap: 12px; margin: 14px 0; }
    .metric { background: #fff; border: 1px solid #d9dde3; border-radius: 8px; padding: 12px 14px; }
    .metric strong { display: block; font-size: 13px; color: #536171; margin-bottom: 5px; }
    .metric b { display: block; font-size: 21px; }
    .metric small { display: block; color: #536171; margin-top: 4px; line-height: 1.3; }
    .good b { color: #16803c; }
    .tradeoff b { color: #9a5b00; }
    .legend span { display: inline-flex; align-items: center; gap: 7px; font-weight: 700; }
    .swatch { width: 28px; height: 5px; border-radius: 3px; display: inline-block; }
    .blue { background: #1f77b4; }
    .red { background: #d62728; }
    .note { max-width: 1080px; margin-top: 14px; color: #4d5a68; line-height: 1.45; }
    code { background: #e9edf2; padding: 2px 5px; border-radius: 4px; }
  </style>
</head>
<body>
  <header>
    <h1>Animacion 2D: estabilizacion del robot auto-balanceado</h1>
    <p>Comparacion visual entre un PID normal y un PID potenciado por IA. La inclinacion del cuerpo, la deriva horizontal y el esfuerzo del motor salen del CSV generado por la simulacion 2D.</p>
  </header>
  <main>
    <section class=\"metrics\" aria-label=\"Resumen de mejora\">
      <article class=\"metric good\"><strong>Mejora visible 1</strong><b id=\"peakMetric\">Calculando...</b><small>Menor inclinacion maxima significa que el cuerpo se aleja menos de la vertical.</small></article>
      <article class=\"metric good\"><strong>Mejora visible 2</strong><b id=\"iaeMetric\">Calculando...</b><small>Menor error acumulado significa que pasa mas tiempo cerca de cero grados.</small></article>
      <article class=\"metric tradeoff\"><strong>Costo de la mejora</strong><b id=\"rpmMetric\">Calculando...</b><small>El PID IA puede pedir mas esfuerzo al motor para estabilizar mejor.</small></article>
    </section>
    <section class=\"stage\">
      <canvas id=\"canvas\" width=\"1080\" height=\"560\"></canvas>
      <div class=\"controls\">
        <button id=\"play\" type=\"button\">Pausa</button>
        <button id=\"reset\" type=\"button\">Reset</button>
        <input id=\"slider\" type=\"range\" min=\"0\" max=\"0\" value=\"0\" />
        <select id=\"speed\" aria-label=\"Velocidad\">
          <option value=\"0.5\">0.5x</option>
          <option value=\"1\" selected>1x</option>
          <option value=\"2\">2x</option>
          <option value=\"4\">4x</option>
        </select>
      </div>
      <div class=\"legend\">
        <span><i class=\"swatch blue\"></i>PID normal</span>
        <span><i class=\"swatch red\"></i>PID IA</span>
        <span class=\"readout\" id=\"time\">t = 0.00 s</span>
      </div>
    </section>
    <p class=\"note\">Archivo fuente: <code>pid_vs_pid_ai_2d.csv</code>. Si cambias las ganancias o perturbaciones, vuelve a correr <code>python scripts\\sim_2d_pid_ai.py</code> y despues <code>python scripts\\create_2d_animation.py</code>.</p>
  </main>

<script>
const DATA = __DATA__;
const controllers = Object.keys(DATA);
const canvas = document.getElementById('canvas');
const ctx = canvas.getContext('2d');
const slider = document.getElementById('slider');
const playButton = document.getElementById('play');
const resetButton = document.getElementById('reset');
const speedSelect = document.getElementById('speed');
const timeLabel = document.getElementById('time');
const peakMetric = document.getElementById('peakMetric');
const iaeMetric = document.getElementById('iaeMetric');
const rpmMetric = document.getElementById('rpmMetric');

let frame = 0;
let playing = true;
let lastTimestamp = performance.now();
const totalFrames = Math.max(...controllers.map(name => DATA[name].length));
slider.max = String(totalFrames - 1);

function clamp(value, low, high) {
  return Math.max(low, Math.min(high, value));
}

function summarize(rows) {
  let maxTilt = 0;
  let maxRpm = 0;
  let iae = 0;
  for (let i = 0; i < rows.length; i++) {
    const r = rows[i];
    maxTilt = Math.max(maxTilt, Math.abs(r.tiltDeg));
    maxRpm = Math.max(maxRpm, Math.abs(r.rpm));
    if (i > 0) {
      const dt = r.t - rows[i - 1].t;
      iae += Math.abs(r.tilt) * dt;
    }
  }
  return { maxTilt, maxRpm, iae };
}

function percentLower(base, improved) {
  return base === 0 ? 0 : (base - improved) / base * 100;
}

function updateSummaryMetrics() {
  const normal = summarize(DATA['PID normal']);
  const ai = summarize(DATA['PID IA']);
  const peakGain = percentLower(normal.maxTilt, ai.maxTilt);
  const iaeGain = percentLower(normal.iae, ai.iae);
  const rpmCost = normal.maxRpm === 0 ? 0 : (ai.maxRpm - normal.maxRpm) / normal.maxRpm * 100;
  peakMetric.textContent = peakGain.toFixed(1) + '% menos pico';
  iaeMetric.textContent = iaeGain.toFixed(1) + '% menos error';
  rpmMetric.textContent = (rpmCost >= 0 ? '+' : '') + rpmCost.toFixed(1) + '% RPM max';
}

function rowAt(name, index) {
  const rows = DATA[name];
  return rows[Math.min(index, rows.length - 1)];
}

function drawGauge(x, y, w, label, value, maxValue, color) {
  ctx.fillStyle = '#edf1f5';
  ctx.fillRect(x, y, w, 10);
  const fill = clamp(Math.abs(value) / maxValue, 0, 1) * w;
  ctx.fillStyle = color;
  ctx.fillRect(x, y, fill, 10);
  ctx.fillStyle = '#34404d';
  ctx.font = '13px Arial';
  ctx.fillText(label + ': ' + value.toFixed(1), x, y - 6);
}

function drawRobot(panel, row, color, title) {
  const groundY = panel.y + panel.h - 88;
  const centerX = panel.x + panel.w / 2;
  const scaleX = 92;
  const wheelR = 24;
  const axleY = groundY - wheelR;
  const axleX = clamp(centerX + row.x * scaleX, panel.x + 58, panel.x + panel.w - 58);
  const theta = row.tilt;

  ctx.save();
  ctx.fillStyle = '#ffffff';
  ctx.strokeStyle = '#d2d8df';
  ctx.lineWidth = 1;
  ctx.fillRect(panel.x, panel.y, panel.w, panel.h);
  ctx.strokeRect(panel.x, panel.y, panel.w, panel.h);

  ctx.fillStyle = '#1f2933';
  ctx.font = 'bold 19px Arial';
  ctx.fillText(title, panel.x + 18, panel.y + 30);
  ctx.font = '14px Arial';
  ctx.fillStyle = '#536171';
  ctx.fillText('tilt ' + row.tiltDeg.toFixed(2) + ' deg', panel.x + 18, panel.y + 55);
  ctx.fillText('x ' + row.x.toFixed(3) + ' m', panel.x + 18, panel.y + 76);
  ctx.fillText('rpm ' + row.rpm.toFixed(1), panel.x + 18, panel.y + 97);
  ctx.fillText('Kp ' + row.kp.toFixed(2), panel.x + panel.w - 112, panel.y + 55);
  ctx.fillText('rec IA ' + row.recovery.toFixed(2), panel.x + panel.w - 112, panel.y + 76);

  ctx.strokeStyle = '#9aa5b1';
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.moveTo(panel.x + 26, groundY);
  ctx.lineTo(panel.x + panel.w - 26, groundY);
  ctx.stroke();

  ctx.strokeStyle = '#c2c8d0';
  ctx.setLineDash([5, 7]);
  ctx.beginPath();
  ctx.moveTo(centerX, panel.y + 116);
  ctx.lineTo(centerX, groundY + 28);
  ctx.stroke();
  ctx.setLineDash([]);

  ctx.strokeStyle = '#b5bdc7';
  ctx.lineWidth = 1;
  for (let i = -3; i <= 3; i++) {
    const tx = centerX + i * scaleX * 0.5;
    ctx.beginPath();
    ctx.moveTo(tx, groundY - 6);
    ctx.lineTo(tx, groundY + 6);
    ctx.stroke();
  }

  ctx.save();
  ctx.translate(axleX, axleY);
  ctx.rotate(-theta);
  ctx.fillStyle = color;
  ctx.strokeStyle = '#17202a';
  ctx.lineWidth = 2;
  ctx.fillRect(-26, -148, 52, 140);
  ctx.strokeRect(-26, -148, 52, 140);
  ctx.fillStyle = 'rgba(255,255,255,0.38)';
  ctx.fillRect(-18, -132, 36, 40);
  ctx.fillStyle = '#111827';
  ctx.beginPath();
  ctx.arc(0, -96, 5, 0, Math.PI * 2);
  ctx.fill();
  ctx.restore();

  ctx.fillStyle = '#111827';
  ctx.beginPath();
  ctx.arc(axleX - 28, axleY, wheelR, 0, Math.PI * 2);
  ctx.fill();
  ctx.beginPath();
  ctx.arc(axleX + 28, axleY, wheelR, 0, Math.PI * 2);
  ctx.fill();
  ctx.strokeStyle = '#f8fafc';
  ctx.lineWidth = 3;
  const spin = row.t * row.rpm * 0.035;
  for (const wx of [axleX - 28, axleX + 28]) {
    ctx.beginPath();
    ctx.moveTo(wx, axleY);
    ctx.lineTo(wx + Math.cos(spin) * wheelR * 0.75, axleY + Math.sin(spin) * wheelR * 0.75);
    ctx.stroke();
  }

  drawGauge(panel.x + 18, panel.y + panel.h - 50, panel.w - 36, 'motor rpm', row.rpm, 240, color);
  drawGauge(panel.x + 18, panel.y + panel.h - 20, panel.w - 36, 'error deg', row.tiltDeg, 45, color);

  ctx.restore();
}

function draw() {
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  ctx.fillStyle = '#eef2f5';
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  const normal = rowAt('PID normal', frame);
  const ai = rowAt('PID IA', frame);
  drawRobot({x: 24, y: 22, w: 506, h: 500}, normal, '#1f77b4', 'PID normal');
  drawRobot({x: 550, y: 22, w: 506, h: 500}, ai, '#d62728', 'PID potenciado por IA');
  const t = Math.max(normal.t, ai.t);
  timeLabel.textContent = 't = ' + t.toFixed(2) + ' s';
  slider.value = String(frame);
}

function tick(timestamp) {
  const dtMs = timestamp - lastTimestamp;
  const speed = Number(speedSelect.value);
  if (playing && dtMs > 42 / speed) {
    frame = (frame + 1) % totalFrames;
    lastTimestamp = timestamp;
    draw();
  }
  requestAnimationFrame(tick);
}

playButton.addEventListener('click', () => {
  playing = !playing;
  playButton.textContent = playing ? 'Pausa' : 'Play';
});

resetButton.addEventListener('click', () => {
  frame = 0;
  playing = false;
  playButton.textContent = 'Play';
  draw();
});

slider.addEventListener('input', () => {
  frame = Number(slider.value);
  playing = false;
  playButton.textContent = 'Play';
  draw();
});

draw();
requestAnimationFrame(tick);
</script>
</body>
</html>
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create a self-contained HTML animation from the 2D PID CSV.")
    parser.add_argument("--csv", type=Path, default=Path("data") / "sim_2d" / "pid_vs_pid_ai_2d.csv")
    parser.add_argument("--output", type=Path, default=Path("data") / "sim_2d" / "pid_vs_pid_ai_2d_animation.html")
    parser.add_argument("--stride", type=int, default=8, help="Keep one frame every N CSV rows.")
    return parser.parse_args()


def load_rows(csv_path: Path, stride: int) -> dict[str, list[dict[str, float]]]:
    grouped: dict[str, list[dict[str, float]]] = {}
    counters: dict[str, int] = {}
    with csv_path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = row["controller"]
            count = counters.get(name, 0)
            counters[name] = count + 1
            if count % stride != 0:
                continue
            grouped.setdefault(name, []).append(
                {
                    "t": float(row["time_s"]),
                    "tilt": float(row["tilt_rad"]),
                    "tiltDeg": float(row["tilt_deg"]),
                    "x": float(row["x_m"]),
                    "rpm": float(row["command_motor_rpm"]),
                    "kp": float(row["kp"]),
                    "recovery": float(row["expert_recovery"]),
                }
            )
    required = {"PID normal", "PID IA"}
    missing = required.difference(grouped)
    if missing:
        raise ValueError(f"CSV missing controllers: {', '.join(sorted(missing))}")
    return grouped


def main() -> None:
    args = parse_args()
    data = load_rows(args.csv, max(1, args.stride))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    html = HTML_TEMPLATE.replace("__DATA__", json.dumps(data, separators=(",", ":")))
    args.output.write_text(html, encoding="utf-8")
    print(f"Animation written: {args.output}")
    print(f"Frames: PID normal={len(data['PID normal'])}, PID IA={len(data['PID IA'])}")


if __name__ == "__main__":
    main()


