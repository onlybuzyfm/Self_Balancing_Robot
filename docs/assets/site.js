(function () {
  "use strict";

  const canvas = document.getElementById("tilt-chart");
  if (!canvas) return;

  const palette = {
    normal: "#2765a8", ai: "#c4513b", grid: "#ded3e2",
    ink: "#2b1733", muted: "#66586c", event: "#087f8c"
  };

  function parseCsv(text) {
    const lines = text.trim().split(/\r?\n/);
    const headers = lines.shift().split(",");
    return lines.map(function (line) {
      const values = line.split(",");
      return Object.fromEntries(headers.map(function (key, index) {
        return [key, values[index]];
      }));
    });
  }

  function resizeCanvas() {
    const ratio = window.devicePixelRatio || 1;
    const rect = canvas.getBoundingClientRect();
    canvas.width = Math.max(1, Math.floor(rect.width * ratio));
    canvas.height = Math.max(1, Math.floor(rect.height * ratio));
    const ctx = canvas.getContext("2d");
    ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
    return { ctx: ctx, width: rect.width, height: rect.height };
  }

  function draw(rows) {
    const target = resizeCanvas();
    const ctx = target.ctx;
    const width = target.width;
    const height = target.height;
    const margin = { left: 54, right: 22, top: 22, bottom: 42 };
    const plot = {
      x: margin.left, y: margin.top,
      w: width - margin.left - margin.right,
      h: height - margin.top - margin.bottom
    };
    const byController = {
      "PID normal": rows.filter(function (row) { return row.controller === "PID normal"; }),
      "PID IA": rows.filter(function (row) { return row.controller === "PID IA"; })
    };
    const maxT = Math.max.apply(null, rows.map(function (row) { return Number(row.time_s); }));
    const maxAbs = Math.max.apply(null, [18].concat(rows.map(function (row) { return Math.abs(Number(row.tilt_deg)); })));
    const minY = -maxAbs;
    const maxY = maxAbs;
    const sx = function (t) { return plot.x + (t / maxT) * plot.w; };
    const sy = function (v) { return plot.y + ((maxY - v) / (maxY - minY)) * plot.h; };

    ctx.clearRect(0, 0, width, height);
    ctx.fillStyle = "#ffffff";
    ctx.fillRect(0, 0, width, height);
    ctx.font = "12px Roboto, Arial, sans-serif";
    ctx.textBaseline = "middle";

    for (let i = 0; i <= 4; i += 1) {
      const value = minY + ((maxY - minY) * i) / 4;
      const y = sy(value);
      ctx.strokeStyle = palette.grid;
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(plot.x, y);
      ctx.lineTo(plot.x + plot.w, y);
      ctx.stroke();
      ctx.fillStyle = palette.muted;
      ctx.textAlign = "right";
      ctx.fillText(value.toFixed(0) + "°", plot.x - 9, y);
    }

    for (let i = 0; i <= 6; i += 1) {
      const value = (maxT * i) / 6;
      const x = sx(value);
      ctx.fillStyle = palette.muted;
      ctx.textAlign = "center";
      ctx.fillText(value.toFixed(0) + " s", x, plot.y + plot.h + 22);
    }

    const eventX = sx(4);
    ctx.strokeStyle = palette.event;
    ctx.lineWidth = 2;
    ctx.setLineDash([6, 5]);
    ctx.beginPath();
    ctx.moveTo(eventX, plot.y);
    ctx.lineTo(eventX, plot.y + plot.h);
    ctx.stroke();
    ctx.setLineDash([]);
    ctx.fillStyle = palette.event;
    ctx.textAlign = "left";
    ctx.fillText("perturbación", Math.min(eventX + 7, width - 85), plot.y + 10);

    Object.keys(byController).forEach(function (name) {
      const values = byController[name];
      ctx.strokeStyle = name === "PID IA" ? palette.ai : palette.normal;
      ctx.lineWidth = 2.2;
      ctx.beginPath();
      values.forEach(function (row, index) {
        const x = sx(Number(row.time_s));
        const y = sy(Number(row.tilt_deg));
        if (index === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      });
      ctx.stroke();
    });

    ctx.strokeStyle = palette.ink;
    ctx.lineWidth = 1;
    ctx.strokeRect(plot.x, plot.y, plot.w, plot.h);
  }

  fetch("pid_vs_pid_ai_2d.csv")
    .then(function (response) {
      if (!response.ok) throw new Error("CSV unavailable");
      return response.text();
    })
    .then(function (text) {
      const rows = parseCsv(text);
      draw(rows);
      window.addEventListener("resize", function () { draw(rows); });
      canvas.setAttribute("aria-label", "Curvas de inclinación simulada de PID normal y PID IA con perturbación en cuatro segundos");
    })
    .catch(function () {
      const target = resizeCanvas();
      target.ctx.fillStyle = palette.muted;
      target.ctx.font = "16px Roboto, Arial, sans-serif";
      target.ctx.textAlign = "center";
      target.ctx.fillText("La gráfica se carga al servir esta página por HTTP.", target.width / 2, target.height / 2);
    });
})();

