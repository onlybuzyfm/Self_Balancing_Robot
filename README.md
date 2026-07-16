# Tumbller Gazebo Digital Twin

Modelo digital inicial para simular un robot auto-balanceado tipo Tumbller en Gazebo Sim y probar controladores, incluido un enfoque Mixture of Experts (MoE), antes de tener el hardware real.

## Objetivo

Este workspace arranca con una version aproximada del robot:

- Chasis alto de dos ruedas, modelado como pendulo invertido.
- Dos ruedas con joints independientes.
- IMU simulada montada en el chasis.
- Sensores de estado publicables hacia ROS 2 via `ros_gz_bridge`.
- Controlador Python inicial con expertos Controller Balance y una compuerta simple.
- Entorno Docker reproducible para compartir con estudiantes.

Cuando llegue el robot real, calibraremos masa, radio de rueda, distancia entre ruedas, altura del centro de masa, limites de motor y orientacion real del IMU.

## Estructura

```text
.
|-- config/
|   |-- bridge.yaml
|   `-- robot_params.yaml
|-- docker/
|   |-- build.sh
|   |-- entrypoint.sh
|   |-- run-gui-linux.sh
|   |-- run-headless.sh
|   `-- shell.sh
|-- launch/
|   |-- sim.launch.py
|   `-- sim_headless.launch.py
|-- models/tumbller/
|   |-- model.config
|   `-- model.sdf
|-- scripts/
|   `-- moe_balance_controller.py
|-- worlds/
|   `-- tumbller_lab.sdf
|-- compose.yaml
|-- Dockerfile
|-- package.xml
`-- CMakeLists.txt
```

## Opcion recomendada para clase: Docker

La imagen usa Ubuntu/ROS 2 Jazzy con Gazebo y `ros_gz`. Esto evita instalar ROS en cada maquina de estudiante.

### 1. Instalar requisitos del host

- Docker Desktop en Windows/macOS, o Docker Engine en Linux.
- En Windows, lo mas comodo es usar Docker Desktop con backend WSL2.
- Para GUI de Gazebo en Windows, abre el proyecto desde WSL2 con WSLg. Si no, usa modo headless.

### 2. Construir la imagen

```bash
docker compose build
```

O en Linux/WSL2:

```bash
./docker/build.sh
```

### 3. Correr simulacion headless

Este modo no abre ventana grafica. Sirve para probar controladores, datasets, CI y maquinas con pocos recursos.

```bash
docker compose up sim
```

### 4. Entrar al contenedor

```bash
docker compose run --rm sim bash
```

Dentro del contenedor ya quedan cargados ROS 2 y el workspace:

```bash
ros2 topic list
ros2 launch tumbller_gazebo sim_headless.launch.py
```

### 5. Correr Gazebo con GUI en Linux/WSL2

Desde Linux o WSL2 con soporte grafico:

```bash
./docker/run-gui-linux.sh
```

Si estas en Windows puro con PowerShell, primero prueba headless. Para GUI es mejor entrar por WSL2 porque Gazebo necesita acceso a servidor grafico.

## Ejecutar sin Docker

Si ya tienes Ubuntu 24.04 con ROS 2 Jazzy:

```bash
sudo apt update
sudo apt install ros-jazzy-ros-gz ros-jazzy-robot-state-publisher python3-colcon-common-extensions
```

En un workspace ROS 2:

```bash
colcon build --symlink-install
source install/setup.bash
ros2 launch tumbller_gazebo sim.launch.py
```

## Siguiente paso tecnico

1. Ajustar el SDF con medidas reales cuando llegue el Tumbller.
2. Reemplazar la compuerta MoE heuristica por una red o reglas entrenadas.
3. Grabar episodios de Gazebo como dataset: inclinacion, velocidad angular, comandos de rueda y recuperacion.
4. Validar primero en simulacion con perturbaciones, luego en hardware con limites de velocidad bajos.

No pruebes politicas nuevas directamente en el robot fisico sin un interruptor de emergencia y limites conservadores de motor.
## Reset desde Gazebo

En la ventana grafica de Gazebo puedes usar el boton de reset del toolbar para volver el mundo a la pose inicial. El `balance_controller` usa tiempo simulado, asi que cuando Gazebo reinicia el reloj, el controlador limpia su integral y manda velocidad cero antes del siguiente intento.

Desde una terminal dentro del contenedor tambien puedes resetear con:

```bash
ros2 run tumbller_gazebo reset_simulation.py
```
## Control teorico

El `balance_controller` usa una aproximacion lineal del pendulo invertido sobre base movil:

```text
theta_ddot = (g / L) * theta - x_ddot / L
x_ddot = g*theta + L*(wn^2*theta + 2*zeta*wn*theta_dot)
wheel_speed = integral(x_ddot) / wheel_radius
```

Los parametros principales estan en `config/pid_params.yaml`:

- `center_of_mass_height_m`: altura aproximada del centro de masa.
- `wheel_radius_m`: radio de rueda.
- `natural_frequency_rad_s`: rapidez de respuesta.
- `damping_ratio`: amortiguamiento.
- `base_velocity_leak`: reduce deriva de velocidad al no tener todavia odometria de rueda.
- `command_sign`: cambia entre `1.0` y `-1.0` si el robot corrige hacia el lado contrario.
## Observer y odometria

El nodo `balance_observer` publica odometria estimada e instrumentacion para ver que pasa con sensores y motores:

```bash
ros2 topic echo /tumbller/imu
ros2 topic echo /tumbller/odom
ros2 topic echo /joint_states
ros2 topic echo /tumbller/observer/pitch_rad
ros2 topic echo /tumbller/observer/pitch_rate_rad_s
ros2 topic echo /tumbller/observer/base_velocity_m_s
ros2 topic echo /tumbller/observer/left_wheel_speed_rad_s
ros2 topic echo /tumbller/observer/right_wheel_speed_rad_s
```

La odometria actual se estima integrando los comandos enviados a las ruedas. Es suficiente para depurar el controlador; despues se puede cambiar a feedback real de joints/encoders.
## CSV de datos

El nodo `balance_csv_logger` guarda cada corrida en:

```text
data/logs/balance_run_YYYYMMDD_HHMMSS.csv
```

Columnas principales:

- `ros_time_s`
- `imu_pitch_rad`, `imu_pitch_rate_rad_s`
- `controller_wheel_cmd_rad_s`, `controller_base_accel_m_s2`
- `left_wheel_speed_rad_s`, `right_wheel_speed_rad_s`
- `observer_base_velocity_m_s`
- `odom_x_m`, `odom_y_m`, `odom_yaw_rad`

Para ver el ultimo log desde WSL:

```bash
ls -lt data/logs/*.csv | head
```
## Simulacion 2D: PID normal vs PID potenciado por IA

Antes de probar cambios en Gazebo, puedes correr un banco de pruebas 2D del robot como pendulo invertido sobre ruedas. Compara un PID fijo contra un PID con mezcla de expertos que ajusta `Kp`, `Ki` y `Kd` segun inclinacion, velocidad angular y deriva de posicion.

```bash
python scripts/sim_2d_pid_ai.py
```

El script genera:

```text
data/sim_2d/pid_vs_pid_ai_2d.csv
data/sim_2d/pid_vs_pid_ai_2d.html
```

Abre el HTML en el navegador para ver las curvas de inclinacion, comando de aceleracion, deriva, RPM equivalente, ganancias adaptativas y peso del experto de recuperacion. Puedes cambiar el escenario con:

```bash
python scripts/sim_2d_pid_ai.py --initial-tilt-deg 10 --impulse-accel -3.0 --duration 15
```

Este modelo 2D no reemplaza Gazebo; sirve para probar rapidamente ideas de control antes de llevarlas al SDF 3D y despues al robot fisico.
Para generar una animacion visual de la estabilizacion:

```bash
python scripts/create_2d_animation.py
```

Luego abre:

```text
data/sim_2d/pid_vs_pid_ai_2d_animation.html
```
Version recomendada para clase en un solo HTML:

```bash
python scripts/create_2d_compendium.py
```

Abre:

```text
data/sim_2d/guia_compendio_pid_ia_2d.html
```
PDF teorico para clase:

```bash
python scripts/create_theoretical_pdf.py
```

Archivo generado:

```text
docs/informe_teorico_pid_ia_robot_auto_balanceado.pdf
```
Compendio para enviar a estudiantes:

```text
docs/compendio_estudiantes_ejecucion_simulacion.html
docs/compendio_estudiantes_ejecucion_simulacion.md
```

Incluye requisitos, comandos de ejecucion, archivos generados, Gazebo/Docker opcional, errores comunes y actividad de entrega.
