# Exposición - Robot autoequilibrado PerceptIA

Entregables para una exposición técnica de aproximadamente 10 minutos, construidos únicamente con información comprobable del repositorio.

## Archivos

- [Presentación editable](Presentacion_PerceptIA_Robot_Autoequilibrado.pptx)
- [Diapositivas en PDF](Diapositivas_PerceptIA_Robot_Autoequilibrado.pdf)
- [Guion de exposición](Guion_Exposicion_Robot_10_min.pdf)

## Estructura de la presentación

1. Proyecto y alcance de la evidencia.
2. Problema del péndulo invertido y objetivos.
3. Arquitectura del ciclo de control.
4. Componentes mecánicos, sensores, actuadores y software.
5. Modelo matemático y principio de equilibrio.
6. PID normal y PID adaptativo por mezcla de expertos.
7. Escenario experimental y perturbación.
8. Resultados y costo de control.
9. Página web y demostración.
10. Conclusiones, limitaciones y siguientes pasos.

## Datos usados

El escenario 2D por defecto tiene una duración de 12 s, inclinación inicial de 7°, perturbación de -2,5 m/s² durante 0,12 s en t=4 s y umbral de caída de 45°.

| Métrica simulada | PID normal | PID IA |
|---|---:|---:|
| Caída | No | No |
| Pico angular | 15,95° | 14,64° |
| IAE | 1,5025 | 1,3484 |
| Deriva final `|x|` | 0,129 m | 0,094 m |
| Pico equivalente de motor | 100,9 rpm | 133,3 rpm |

La mezcla de expertos es heurística y transparente. No se presenta como una red entrenada ni como una prueba física.

## Guion

La parte hablada contiene 1.127 palabras y asigna un tiempo recomendado a cada diapositiva. Incluye:

- transiciones naturales;
- indicaciones de qué mostrar;
- demostración de la página y la animación;
- preguntas probables del jurado con respuestas breves.

La página final de preguntas no forma parte de los 10 minutos.

## Demostración recomendada

1. Abrir [la página pública](https://onlybuzyfm.github.io/Self_Balancing_Robot/).
2. Señalar la etiqueta que identifica los datos como simulados.
3. Mostrar la perturbación marcada en t=4 s.
4. Comparar inclinación, deriva y RPM.
5. Abrir la animación, pulsar reinicio y reproducirla a una velocidad cómoda.

## Verificación realizada

- PowerPoint de 10 diapositivas en formato 16:9.
- Fuente Roboto e identidad visual de PerceptIA.
- SVG oficial del pájaro incrustado en la presentación.
- PDF de diapositivas exportado directamente desde PowerPoint.
- Las 10 diapositivas se renderizaron e inspeccionaron individualmente.
- El guion se renderizó en 12 páginas y se revisó visualmente.
- No se modificaron los algoritmos de control.

## Fuentes internas

- `README.md`
- `scripts/sim_2d_pid_ai.py`
- `scripts/balance_controller.py`
- `scripts/moe_balance_controller.py`
- `config/pid_params.yaml`
- `config/robot_params.yaml`
- `models/tumbller/model.sdf`
- `docs/pid_vs_pid_ai_2d.csv`

## Limitación principal

Los parámetros físicos de Gazebo son estimaciones iniciales. Antes de probar en hardware deben medirse y calibrarse la masa, la geometría, el centro de masa, la orientación de la IMU, el signo de los motores y sus límites.

