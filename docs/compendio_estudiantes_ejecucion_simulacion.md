# Compendio para estudiantes: ejecucion de la simulacion del robot auto-balanceado

## 1. Proposito

Este documento explica como ejecutar las simulaciones del proyecto del robot auto-balanceado de dos ruedas. El objetivo es que cada estudiante pueda correr el modelo 2D, analizar el comportamiento del PID normal y del PID potenciado por IA, abrir las graficas, revisar el compendio interactivo y, si tiene Docker configurado, probar tambien la simulacion en Gazebo.

## 2. Que contiene el proyecto

El proyecto incluye:

- Simulacion 2D del robot como pendulo invertido.
- Comparacion entre PID normal y PID potenciado por IA.
- Archivo CSV con datos de la simulacion.
- Graficas HTML.
- Animacion interactiva.
- Compendio HTML con guia, graficas y animacion.
- PDF teorico.
- Simulacion Gazebo/ROS 2 mediante Docker.

## 3. Requisitos minimos

Para la simulacion 2D:

- Windows, Linux o macOS.
- Python 3 instalado.
- Navegador web.

Para Gazebo/ROS 2:

- Docker Desktop instalado.
- En Windows, Docker Desktop con backend WSL2.
- Suficiente memoria disponible para correr Gazebo.

La simulacion 2D no necesita ROS, Gazebo ni Docker.

## 4. Ubicacion del proyecto

En la computadora de trabajo, el proyecto se encuentra en:

```text
D:\PercetptIA\Self_Balancing_Robot
```

Si el estudiante tiene el proyecto en otra carpeta, debe entrar a su propia ruta.

Ejemplo en PowerShell:

```powershell
cd D:\PercetptIA\Self_Balancing_Robot
```

## 5. Ejecutar la simulacion 2D

Desde la carpeta raiz del proyecto:

```powershell
python scripts\sim_2d_pid_ai.py
```

Este comando genera:

```text
data\sim_2d\pid_vs_pid_ai_2d.csv
data\sim_2d\pid_vs_pid_ai_2d.html
```

El CSV contiene los datos numericos. El HTML contiene graficas del comportamiento del robot.

## 6. Abrir el compendio interactivo recomendado

La version recomendada para clase es el compendio en un solo HTML:

```text
data\sim_2d\guia_compendio_pid_ia_2d.html
```

Para regenerarlo despues de ejecutar la simulacion:

```powershell
python scripts\create_2d_compendium.py
```

Luego abrir el archivo HTML en el navegador.

Este compendio incluye:

- Explicacion del modelo 2D.
- PID normal.
- PID potenciado por IA.
- Tabla de resultados.
- Animacion interactiva.
- Graficas principales.
- Actividades para estudiantes.

## 7. Generar solo la animacion

Si se desea generar unicamente la animacion:

```powershell
python scripts\create_2d_animation.py
```

Archivo generado:

```text
data\sim_2d\pid_vs_pid_ai_2d_animation.html
```

La animacion muestra lado a lado:

- PID normal.
- PID potenciado por IA.
- Inclinacion del robot.
- Posicion horizontal.
- RPM aproximadas.
- Ganancia Kp.
- Peso del experto de recuperacion.

## 8. Generar el PDF teorico

Para crear el PDF teorico:

```powershell
python scripts\create_theoretical_pdf.py
```

Archivo generado:

```text
docs\informe_teorico_pid_ia_robot_auto_balanceado.pdf
```

El PDF contiene fundamentos teoricos sobre:

- Pendulo invertido.
- Dinamica simplificada.
- PID clasico.
- PID potenciado por IA.
- Mezcla de expertos.
- Metricas de comparacion.
- Conexion con Gazebo y robot fisico.

## 9. Ejecutar escenarios personalizados

Se puede cambiar la inclinacion inicial:

```powershell
python scripts\sim_2d_pid_ai.py --initial-tilt-deg 10
python scripts\create_2d_compendium.py
```

Se puede cambiar la perturbacion externa:

```powershell
python scripts\sim_2d_pid_ai.py --impulse-accel -5.0
python scripts\create_2d_compendium.py
```

Se puede cambiar la duracion de la simulacion:

```powershell
python scripts\sim_2d_pid_ai.py --duration 15
python scripts\create_2d_compendium.py
```

## 10. Interpretacion basica de resultados

Al abrir el compendio HTML, observar tres aspectos:

1. **Inclinacion maxima**

   Indica cuanto se aleja el robot de la vertical. Menor valor significa mejor estabilidad.

2. **Error acumulado**

   Indica cuanto tiempo pasa el robot lejos del angulo objetivo. Menor valor significa mejor control global.

3. **RPM maxima**

   Indica el esfuerzo solicitado al motor. Una mejora en estabilidad puede requerir mas RPM.

La conclusion esperada es que el PID potenciado por IA puede reducir la inclinacion y el error acumulado, pero usando mayor esfuerzo de motor.

## 11. Ejecutar Gazebo con Docker

Primero verificar que Docker Desktop este abierto y funcionando.

Construir la imagen:

```powershell
docker compose build
```

Ejecutar simulacion headless:

```powershell
docker compose up sim
```

Ejecutar una terminal dentro del contenedor:

```powershell
docker compose run --rm sim bash
```

Dentro del contenedor se pueden consultar topics de ROS 2:

```bash
ros2 topic list
```

## 12. Gazebo grafico

Para abrir Gazebo con interfaz grafica, lo mas recomendable en Windows es usar WSL2 con soporte grafico.

Desde Linux/WSL2:

```bash
./docker/run-gui-linux.sh
```

Si la computadora no tiene configuracion grafica correcta, usar primero la simulacion 2D y el modo headless.

## 13. Errores comunes

### Error: Docker no conecta

Mensaje posible:

```text
error during connect: dockerDesktopLinuxEngine
```

Solucion:

- Abrir Docker Desktop.
- Esperar a que el motor este iniciado.
- Revisar que WSL2 este habilitado.
- Volver a ejecutar el comando.

### Error: python no se reconoce

Solucion:

- Instalar Python 3.
- Marcar la opcion “Add Python to PATH”.
- Cerrar y abrir PowerShell nuevamente.

### No se abre el HTML

Solucion:

- Ir a la carpeta `data\sim_2d`.
- Doble clic sobre el archivo `.html`.
- Tambien puede abrirse desde el navegador con `Ctrl + O`.

### La simulacion parece no cambiar

Solucion:

- Ejecutar de nuevo `python scripts\sim_2d_pid_ai.py`.
- Regenerar el compendio con `python scripts\create_2d_compendium.py`.
- Refrescar el navegador con `Ctrl + R`.

## 14. Actividad para entregar

Cada estudiante debe entregar:

1. Captura del compendio HTML abierto.
2. Una tabla comparando PID normal y PID IA.
3. Respuesta breve a estas preguntas:

   - Cual controlador tuvo menor inclinacion maxima?
   - Cual tuvo menor error acumulado?
   - Cual uso mas RPM?
   - La mejora del PID IA fue gratuita o tuvo un costo?
   - Que podria pasar al llevar este control a Gazebo o al robot fisico?

## 15. Comandos rapidos

Ejecutar todo lo principal:

```powershell
cd D:\PercetptIA\Self_Balancing_Robot
python scripts\sim_2d_pid_ai.py
python scripts\create_2d_compendium.py
python scripts\create_theoretical_pdf.py
```

Abrir archivos principales:

```text
data\sim_2d\guia_compendio_pid_ia_2d.html
docs\informe_teorico_pid_ia_robot_auto_balanceado.pdf
```
