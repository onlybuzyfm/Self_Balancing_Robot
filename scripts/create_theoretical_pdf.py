#!/usr/bin/env python3
"""Generate a theoretical PDF for the 2D self-balancing robot PID project.

This script intentionally uses only the Python standard library. It writes a
simple PDF with standard Type1 fonts so it can run on student machines without
extra dependencies.
"""

from __future__ import annotations

import csv
import math
from pathlib import Path
from typing import Iterable

PAGE_W = 595.0
PAGE_H = 842.0
MARGIN = 54.0


class PdfBuilder:
    def __init__(self) -> None:
        self.objects: list[bytes] = []
        self.pages: list[int] = []
        self.font_regular = self.add_object(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
        self.font_bold = self.add_object(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>")
        self.font_italic = self.add_object(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Oblique >>")

    def add_object(self, payload: bytes) -> int:
        self.objects.append(payload)
        return len(self.objects)

    def add_page(self, commands: list[str]) -> None:
        stream = "\n".join(commands).encode("cp1252", errors="replace")
        content_obj = self.add_object(
            b"<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n" + stream + b"\nendstream"
        )
        page_obj = self.add_object(
            (
                f"<< /Type /Page /Parent 0 0 R /MediaBox [0 0 {PAGE_W:.0f} {PAGE_H:.0f}] "
                f"/Resources << /Font << /F1 {self.font_regular} 0 R /F2 {self.font_bold} 0 R /F3 {self.font_italic} 0 R >> >> "
                f"/Contents {content_obj} 0 R >>"
            ).encode("ascii")
        )
        self.pages.append(page_obj)

    def write(self, path: Path) -> None:
        kids = " ".join(f"{p} 0 R" for p in self.pages)
        pages_obj = self.add_object(f"<< /Type /Pages /Kids [{kids}] /Count {len(self.pages)} >>".encode("ascii"))
        for page_obj in self.pages:
            self.objects[page_obj - 1] = self.objects[page_obj - 1].replace(b"/Parent 0 0 R", f"/Parent {pages_obj} 0 R".encode("ascii"))
        catalog_obj = self.add_object(f"<< /Type /Catalog /Pages {pages_obj} 0 R >>".encode("ascii"))

        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("wb") as f:
            f.write(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
            offsets = [0]
            for idx, payload in enumerate(self.objects, start=1):
                offsets.append(f.tell())
                f.write(f"{idx} 0 obj\n".encode("ascii"))
                f.write(payload)
                f.write(b"\nendobj\n")
            xref_pos = f.tell()
            f.write(f"xref\n0 {len(self.objects) + 1}\n".encode("ascii"))
            f.write(b"0000000000 65535 f \n")
            for offset in offsets[1:]:
                f.write(f"{offset:010d} 00000 n \n".encode("ascii"))
            f.write(
                (
                    f"trailer\n<< /Size {len(self.objects) + 1} /Root {catalog_obj} 0 R >>\n"
                    f"startxref\n{xref_pos}\n%%EOF\n"
                ).encode("ascii")
            )


def esc(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def cmd_text(x: float, y: float, text: str, size: float = 11, font: str = "F1", color: tuple[float, float, float] = (0, 0, 0)) -> str:
    r, g, b = color
    return f"BT {r:.3f} {g:.3f} {b:.3f} rg /{font} {size:.1f} Tf {x:.1f} {y:.1f} Td ({esc(text)}) Tj ET"


def line(x1: float, y1: float, x2: float, y2: float, width: float = 1, color: tuple[float, float, float] = (0, 0, 0)) -> str:
    r, g, b = color
    return f"q {r:.3f} {g:.3f} {b:.3f} RG {width:.1f} w {x1:.1f} {y1:.1f} m {x2:.1f} {y2:.1f} l S Q"


def rect(x: float, y: float, w: float, h: float, stroke: tuple[float, float, float] = (0, 0, 0), fill: tuple[float, float, float] | None = None, width: float = 1) -> str:
    sr, sg, sb = stroke
    if fill is None:
        return f"q {sr:.3f} {sg:.3f} {sb:.3f} RG {width:.1f} w {x:.1f} {y:.1f} {w:.1f} {h:.1f} re S Q"
    fr, fg, fb = fill
    return f"q {fr:.3f} {fg:.3f} {fb:.3f} rg {sr:.3f} {sg:.3f} {sb:.3f} RG {width:.1f} w {x:.1f} {y:.1f} {w:.1f} {h:.1f} re B Q"


def circle(x: float, y: float, r: float, color: tuple[float, float, float] = (0, 0, 0)) -> str:
    # Bezier approximation for a filled circle.
    k = 0.5522847498 * r
    cr, cg, cb = color
    return (
        f"q {cr:.3f} {cg:.3f} {cb:.3f} rg "
        f"{x:.1f} {y+r:.1f} m {x+k:.1f} {y+r:.1f} {x+r:.1f} {y+k:.1f} {x+r:.1f} {y:.1f} c "
        f"{x+r:.1f} {y-k:.1f} {x+k:.1f} {y-r:.1f} {x:.1f} {y-r:.1f} c "
        f"{x-k:.1f} {y-r:.1f} {x-r:.1f} {y-k:.1f} {x-r:.1f} {y:.1f} c "
        f"{x-r:.1f} {y+k:.1f} {x-k:.1f} {y+r:.1f} {x:.1f} {y+r:.1f} c f Q"
    )


class Page:
    def __init__(self, title: str | None = None, page_no: int | None = None) -> None:
        self.commands: list[str] = []
        self.y = PAGE_H - MARGIN
        if title:
            self.heading(title)
        if page_no is not None:
            self.footer(page_no)

    def footer(self, page_no: int) -> None:
        self.commands.append(line(MARGIN, 36, PAGE_W - MARGIN, 36, 0.6, (0.72, 0.75, 0.78)))
        self.commands.append(cmd_text(MARGIN, 22, "Robot auto-balanceado 2D - PID vs PID IA", 8.5, "F3", (0.35, 0.39, 0.44)))
        self.commands.append(cmd_text(PAGE_W - 88, 22, f"Pagina {page_no}", 8.5, "F1", (0.35, 0.39, 0.44)))

    def heading(self, text: str) -> None:
        self.commands.append(cmd_text(MARGIN, self.y, text, 18, "F2", (0.08, 0.13, 0.18)))
        self.y -= 16
        self.commands.append(line(MARGIN, self.y, PAGE_W - MARGIN, self.y, 1.2, (0.12, 0.47, 0.70)))
        self.y -= 24

    def subheading(self, text: str) -> None:
        self.y -= 8
        self.commands.append(cmd_text(MARGIN, self.y, text, 13.5, "F2", (0.12, 0.22, 0.31)))
        self.y -= 18

    def paragraph(self, text: str, size: float = 10.7, leading: float = 14.5, indent: float = 0) -> None:
        for line_text in wrap_text(text, int((86 - indent / 6) * (10.7 / size))):
            self.commands.append(cmd_text(MARGIN + indent, self.y, line_text, size, "F1", (0.12, 0.15, 0.18)))
            self.y -= leading
        self.y -= 4

    def bullet(self, text: str) -> None:
        lines = wrap_text(text, 78)
        self.commands.append(cmd_text(MARGIN + 7, self.y, "-", 10.5, "F2"))
        self.commands.append(cmd_text(MARGIN + 22, self.y, lines[0], 10.5, "F1"))
        self.y -= 14
        for cont in lines[1:]:
            self.commands.append(cmd_text(MARGIN + 22, self.y, cont, 10.5, "F1"))
            self.y -= 14

    def formula_box(self, lines_text: Iterable[str]) -> None:
        lines_list = list(lines_text)
        h = 20 + len(lines_list) * 15
        self.commands.append(rect(MARGIN, self.y - h + 8, PAGE_W - 2 * MARGIN, h, (0.70, 0.75, 0.80), (0.94, 0.96, 0.98)))
        y = self.y - 14
        for txt in lines_list:
            self.commands.append(cmd_text(MARGIN + 14, y, txt, 10.5, "F1", (0.05, 0.12, 0.18)))
            y -= 15
        self.y -= h + 8


def wrap_text(text: str, width: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = word if not current else f"{current} {word}"
        if len(candidate) <= width:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines or [""]


def load_metrics(csv_path: Path) -> dict[str, dict[str, float]]:
    grouped: dict[str, list[dict[str, float]]] = {}
    if not csv_path.exists():
        return {}
    with csv_path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            grouped.setdefault(row["controller"], []).append(
                {
                    "t": float(row["time_s"]),
                    "tilt": float(row["tilt_rad"]),
                    "tilt_deg": float(row["tilt_deg"]),
                    "x": float(row["x_m"]),
                    "rpm": float(row["command_motor_rpm"]),
                }
            )
    metrics: dict[str, dict[str, float]] = {}
    for name, rows in grouped.items():
        iae = 0.0
        for i in range(1, len(rows)):
            iae += abs(rows[i]["tilt"]) * (rows[i]["t"] - rows[i - 1]["t"])
        metrics[name] = {
            "max_tilt": max(abs(r["tilt_deg"]) for r in rows),
            "iae": iae,
            "max_x": max(abs(r["x"]) for r in rows),
            "max_rpm": max(abs(r["rpm"]) for r in rows),
        }
    return metrics


def add_pendulum_diagram(page: Page) -> None:
    x0, y0 = 300, page.y - 84
    page.commands.append(line(120, y0 - 55, 475, y0 - 55, 1.2, (0.45, 0.48, 0.52)))
    page.commands.append(circle(x0 - 28, y0 - 55, 16, (0.05, 0.06, 0.07)))
    page.commands.append(circle(x0 + 28, y0 - 55, 16, (0.05, 0.06, 0.07)))
    page.commands.append(line(x0, y0 - 55, x0 + 45, y0 + 62, 8, (0.86, 0.16, 0.12)))
    page.commands.append(line(x0, y0 - 55, x0, y0 + 72, 1, (0.12, 0.47, 0.70)))
    page.commands.append(cmd_text(x0 + 51, y0 + 45, "cuerpo inclinado", 9.5, "F2", (0.20, 0.22, 0.25)))
    page.commands.append(cmd_text(x0 + 8, y0 + 20, "theta", 9.5, "F3", (0.12, 0.47, 0.70)))
    page.commands.append(cmd_text(120, y0 - 82, "ruedas / base movil", 9.5, "F1", (0.35, 0.39, 0.44)))
    page.y -= 180


def add_table(page: Page, rows: list[list[str]], widths: list[float]) -> None:
    x = MARGIN
    row_h = 22
    for r, row in enumerate(rows):
        y = page.y - row_h
        fill = (0.91, 0.94, 0.96) if r == 0 else (1, 1, 1)
        page.commands.append(rect(x, y, sum(widths), row_h, (0.78, 0.82, 0.86), fill, 0.7))
        cx = x
        for i, cell in enumerate(row):
            if i > 0:
                page.commands.append(line(cx, y, cx, y + row_h, 0.5, (0.78, 0.82, 0.86)))
            font = "F2" if r == 0 else "F1"
            page.commands.append(cmd_text(cx + 5, y + 7, cell[:38], 8.8, font, (0.08, 0.13, 0.18)))
            cx += widths[i]
        page.y -= row_h
    page.y -= 10


def build_pdf(output: Path, csv_path: Path) -> None:
    pdf = PdfBuilder()
    metrics = load_metrics(csv_path)
    normal = metrics.get("PID normal", {})
    ai = metrics.get("PID IA", {})

    # Page 1: cover
    p = Page()
    p.commands.append(rect(0, 0, PAGE_W, PAGE_H, (1, 1, 1), (0.96, 0.98, 0.99), 0))
    p.commands.append(rect(MARGIN, 560, PAGE_W - 2 * MARGIN, 160, (0.12, 0.47, 0.70), (1, 1, 1), 1.4))
    p.commands.append(cmd_text(MARGIN + 24, 680, "Informe teorico", 18, "F2", (0.12, 0.47, 0.70)))
    p.commands.append(cmd_text(MARGIN + 24, 642, "Robot auto-balanceado 2D", 26, "F2", (0.08, 0.13, 0.18)))
    p.commands.append(cmd_text(MARGIN + 24, 608, "PID clasico vs PID potenciado por IA", 20, "F2", (0.08, 0.13, 0.18)))
    p.commands.append(cmd_text(MARGIN, 500, "Proyecto educativo para simulacion, analisis y comparacion de controladores", 13, "F1", (0.20, 0.24, 0.28)))
    p.commands.append(cmd_text(MARGIN, 474, "Modelo 2D simplificado previo a Gazebo y pruebas en robot fisico", 12, "F3", (0.35, 0.39, 0.44)))
    p.commands.append(cmd_text(MARGIN, 110, "Archivo generado automaticamente desde el proyecto Self_Balancing_Robot", 9.5, "F1", (0.35, 0.39, 0.44)))
    pdf.add_page(p.commands)

    # Page 2: objectives and overview
    p = Page("1. Proposito del informe", 2)
    p.paragraph("Este informe presenta la base teorica para comprender y comparar dos estrategias de control aplicadas a un robot auto-balanceado de dos ruedas: un PID clasico y un PID potenciado por inteligencia artificial mediante mezcla de expertos.")
    p.paragraph("La simulacion 2D permite aislar el problema principal del equilibrio antes de incorporar detalles de Gazebo, como geometria 3D, friccion, colisiones, sensores simulados y configuracion de joints.")
    p.subheading("Objetivos especificos")
    for b in [
        "Explicar por que el robot puede modelarse como un pendulo invertido sobre una base movil.",
        "Relacionar el error angular con la accion de control aplicada a las ruedas.",
        "Distinguir el comportamiento de un PID con ganancias fijas y uno con ganancias adaptativas.",
        "Interpretar metricas como inclinacion maxima, error acumulado y esfuerzo de motor.",
        "Preparar el paso metodologico desde simulacion 2D hacia Gazebo y robot fisico.",
    ]:
        p.bullet(b)
    p.subheading("Flujo recomendado")
    p.formula_box(["Modelo teorico 2D  ->  Simulacion Gazebo 3D  ->  Robot fisico", "Primero se valida la idea de control; despues se agregan realismo y restricciones."])
    pdf.add_page(p.commands)

    # Page 3: model
    p = Page("2. Modelo como pendulo invertido", 3)
    p.paragraph("Un robot auto-balanceado se mantiene de pie desplazando sus ruedas. Si el cuerpo se inclina, la base debe acelerar para que el centro de masa vuelva a una region cercana a la vertical.")
    add_pendulum_diagram(p)
    p.paragraph("La variable principal es theta, el angulo del cuerpo respecto a la vertical. El objetivo del controlador es mantener theta cerca de cero grados, sin exigir velocidades imposibles a los motores.")
    p.formula_box([
        "theta = angulo de inclinacion del cuerpo",
        "theta_dot = velocidad angular",
        "x = posicion horizontal de la base",
        "x_ddot = aceleracion horizontal ordenada por el controlador",
    ])
    p.paragraph("En un modelo simplificado, la gravedad tiende a aumentar la caida del cuerpo, mientras que la aceleracion horizontal de la base puede compensarla. Esta relacion permite estudiar control sin depender inicialmente de un modelo SDF complejo.")
    pdf.add_page(p.commands)

    # Page 4: dynamics
    p = Page("3. Dinamica simplificada", 4)
    p.paragraph("La simulacion 2D usa una aproximacion no lineal sencilla. No pretende representar todos los fenomenos fisicos, pero conserva la intuicion fundamental: el cuerpo cae por gravedad y se recupera acelerando la base.")
    p.formula_box([
        "theta_ddot = (g / L) * sin(theta) - (x_ddot / L) * cos(theta) - d * theta_dot",
        "g = gravedad",
        "L = altura aproximada del centro de masa",
        "d = amortiguamiento angular",
    ])
    p.subheading("Interpretacion")
    for b in [
        "El termino (g / L) * sin(theta) representa la tendencia natural a caer.",
        "El termino -(x_ddot / L) * cos(theta) representa la accion correctiva de las ruedas.",
        "El amortiguamiento reduce oscilaciones y representa perdidas del sistema.",
        "Si el controlador se satura, el robot puede no tener suficiente aceleracion para recuperarse.",
    ]:
        p.bullet(b)
    p.paragraph("Este modelo muestra por que el signo de la accion de control es critico. Si las ruedas aceleran en la direccion incorrecta, el robot ayuda a su propia caida en vez de corregirla.")
    pdf.add_page(p.commands)

    # Page 5: PID
    p = Page("4. Control PID clasico", 5)
    p.paragraph("El PID clasico calcula la accion de control usando tres componentes: proporcional, integral y derivativa. Es una estrategia ampliamente usada porque es simple, interpretable y efectiva cuando se ajusta correctamente.")
    p.formula_box(["u = Kp * error + Ki * integral(error) + Kd * derivative(error)", "error = theta - theta_objetivo"])
    p.subheading("Rol de cada ganancia")
    add_table(
        p,
        [
            ["Ganancia", "Funcion", "Riesgo si es excesiva"],
            ["Kp", "Corrige el error actual", "Oscilacion o saturacion"],
            ["Ki", "Corrige error acumulado", "Windup y respuesta lenta"],
            ["Kd", "Frena cambios rapidos", "Sensibilidad al ruido"],
        ],
        [70, 210, 210],
    )
    p.paragraph("En el robot auto-balanceado, el PID no debe buscar solamente que el angulo sea cero. Tambien debe cuidar que la base no derive indefinidamente hacia adelante o hacia atras.")
    p.formula_box(["theta_objetivo = -(Kx * x + Kv * x_dot)", "El signo negativo pide inclinarse contra la deriva de posicion."])
    pdf.add_page(p.commands)

    # Page 6: AI PID
    p = Page("5. PID potenciado por IA", 6)
    p.paragraph("El PID potenciado por IA conserva la estructura del PID, pero modifica sus ganancias segun el estado del robot. En esta practica se usa una mezcla de expertos transparente y explicable.")
    p.subheading("Expertos usados")
    for b in [
        "Experto de balance: actua cuando el robot esta cerca de la vertical y necesita movimientos suaves.",
        "Experto de recuperacion: actua cuando la inclinacion o la velocidad angular son grandes.",
        "Experto de deriva: actua cuando la base se aleja demasiado de la posicion inicial.",
    ]:
        p.bullet(b)
    p.formula_box([
        "w_balance + w_recuperacion + w_deriva = 1",
        "Kp_final = w1*Kp_balance + w2*Kp_recuperacion + w3*Kp_deriva",
        "El mismo principio se aplica a Ki y Kd.",
    ])
    p.paragraph("Este enfoque es una primera forma de IA porque el controlador cambia su comportamiento de acuerdo con el contexto. Mas adelante, los pesos podrian aprenderse con redes neuronales, logica difusa, algoritmos geneticos o aprendizaje por refuerzo.")
    pdf.add_page(p.commands)

    # Page 7: metrics and results
    p = Page("6. Metricas de evaluacion", 7)
    p.paragraph("Un controlador no debe evaluarse solamente preguntando si el robot cae o no cae. Tambien importa cuanto se inclina, cuanto error acumula y cuanto esfuerzo exige a los motores.")
    p.subheading("Metricas principales")
    for b in [
        "Inclinacion maxima: mayor valor absoluto del angulo durante la simulacion.",
        "IAE: integral del error absoluto; mide cuanto tiempo pasa lejos de la vertical.",
        "RPM maxima: esfuerzo equivalente exigido al motor.",
        "Deriva maxima: desplazamiento horizontal acumulado de la base.",
    ]:
        p.bullet(b)
    if normal and ai:
        p.subheading("Resultado de referencia de la simulacion actual")
        add_table(
            p,
            [
                ["Controlador", "Max tilt", "IAE", "Max x", "Max RPM"],
                ["PID normal", f"{normal['max_tilt']:.2f} deg", f"{normal['iae']:.4f}", f"{normal['max_x']:.3f} m", f"{normal['max_rpm']:.1f}"],
                ["PID IA", f"{ai['max_tilt']:.2f} deg", f"{ai['iae']:.4f}", f"{ai['max_x']:.3f} m", f"{ai['max_rpm']:.1f}"],
            ],
            [105, 95, 95, 95, 95],
        )
        p.paragraph("En esta corrida, el PID IA reduce la inclinacion maxima y el error acumulado, pero solicita mayor esfuerzo de motor. Esta es una conclusion importante: mejorar estabilidad puede tener costo energetico o de actuacion.")
    pdf.add_page(p.commands)

    # Page 8: interpretation
    p = Page("7. Interpretacion educativa", 8)
    p.paragraph("La mejora del PID IA debe observarse en tres niveles: la curva de inclinacion, las metricas numericas y la animacion del cuerpo. Si visualmente ambos robots parecen parecidos, el error acumulado ayuda a cuantificar la diferencia.")
    p.subheading("Como defender la mejora")
    for b in [
        "Menor pico de inclinacion significa que el robot se aleja menos de la vertical.",
        "Menor IAE significa que durante toda la prueba se mantuvo mas cerca del objetivo.",
        "Mayor RPM maxima indica que la mejora no fue gratuita; exigio mas actuacion.",
        "Un buen controlador debe equilibrar estabilidad, energia y limites fisicos del motor.",
    ]:
        p.bullet(b)
    p.subheading("Limitaciones del modelo 2D")
    for b in [
        "No incluye geometria 3D completa ni colisiones complejas.",
        "No representa con precision todos los efectos de friccion rueda-suelo.",
        "No modela saturacion electrica, retardo real del motor ni ruido completo del sensor.",
        "Sirve como banco de pruebas conceptual antes de Gazebo.",
    ]:
        p.bullet(b)
    pdf.add_page(p.commands)

    # Page 9: Gazebo and physical robot
    p = Page("8. Conexion con Gazebo y robot fisico", 9)
    p.paragraph("Una vez que una estrategia funciona en 2D, el siguiente paso es probarla en Gazebo. Alli aparecen problemas que el modelo 2D no incluye: posicion real de los joints, centro de masa, contacto de ruedas, friccion y orientacion de la IMU.")
    p.formula_box(["2D: valida la idea de control", "Gazebo: valida geometria, sensores y contacto", "Robot fisico: valida actuadores, bateria, latencia y seguridad"])
    p.subheading("Recomendaciones de seguridad")
    for b in [
        "Limitar RPM y aceleracion antes de probar en hardware real.",
        "Agregar interruptor de emergencia o forma rapida de detener motores.",
        "Probar primero con inclinaciones pequenas y superficies despejadas.",
        "Registrar datos de IMU, comandos y velocidad de ruedas para comparar con simulacion.",
    ]:
        p.bullet(b)
    pdf.add_page(p.commands)

    # Page 10: activities and closure
    p = Page("9. Actividades y preguntas", 10)
    p.subheading("Actividades sugeridas")
    for b in [
        "Ejecutar la simulacion con inclinacion inicial de 3, 10 y 15 grados; comparar metricas.",
        "Aumentar la perturbacion externa y observar cuando se activa el experto de recuperacion.",
        "Modificar Kp, Ki y Kd del PID normal y analizar oscilaciones o saturacion.",
        "Comparar la animacion con las graficas para conectar movimiento y datos.",
    ]:
        p.bullet(b)
    p.subheading("Preguntas de reflexion")
    for b in [
        "Por que el robot auto-balanceado se parece a un pendulo invertido?",
        "Que ocurre si el signo del controlador esta invertido?",
        "Por que un PID IA puede ser mejor en error pero peor en esfuerzo de motor?",
        "Que metricas faltarian para decidir si el controlador es seguro en hardware real?",
    ]:
        p.bullet(b)
    p.subheading("Archivos relacionados")
    p.formula_box([
        "scripts/sim_2d_pid_ai.py",
        "scripts/create_2d_compendium.py",
        "data/sim_2d/guia_compendio_pid_ia_2d.html",
        "data/sim_2d/pid_vs_pid_ai_2d.csv",
    ])
    pdf.add_page(p.commands)

    pdf.write(output)


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    output = root / "docs" / "informe_teorico_pid_ia_robot_auto_balanceado.pdf"
    csv_path = root / "data" / "sim_2d" / "pid_vs_pid_ai_2d.csv"
    build_pdf(output, csv_path)
    print(f"PDF teorico generado: {output}")


if __name__ == "__main__":
    main()
