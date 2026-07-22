# Informe educativo: Simulacion 2D de un robot auto-balanceado con PID normal y PID potenciado por IA

## 1. Titulo del proyecto

**Simulacion 2D y comparacion de controladores para un robot auto-balanceado de dos ruedas: PID clasico vs PID potenciado por inteligencia artificial**

## 2. Objetivo general

El objetivo de esta practica es que el estudiante comprenda el comportamiento dinamico de un robot auto-balanceado de dos ruedas mediante una simulacion 2D simplificada, comparando un controlador PID clasico con una version potenciada por inteligencia artificial basada en mezcla de expertos.

La simulacion permite estudiar el control del equilibrio antes de pasar a una simulacion 3D en Gazebo o a pruebas con el robot fisico real.

## 3. Contexto del problema

Un robot auto-balanceado de dos ruedas se comporta de forma parecida a un pendulo invertido. A diferencia de un pendulo normal, que cuelga hacia abajo de manera estable, el robot debe mantenerse de pie sobre sus ruedas.

Si el cuerpo del robot se inclina hacia adelante, las ruedas deben moverse de manera adecuada para recuperar el equilibrio. Si se inclina hacia atras, ocurre lo mismo en sentido contrario. El reto principal consiste en calcular que tan rapido y en que direccion deben girar los motores para mantener el angulo del cuerpo cerca de cero grados.

En esta practica se analiza el problema en 2D, considerando solamente el movimiento hacia adelante y hacia atras. Esto permite estudiar primero la logica de control sin depender de problemas geometricos, friccion compleja, sensores simulados o errores del modelo 3D.

## 4. Modelo simplificado del robot

El robot se aproxima como un pendulo invertido sobre una base movil. La variable mas importante es el angulo de inclinacion:

```text
theta = angulo del cuerpo respecto a la vertical
```

Cuando:

```text
theta = 0
```

el robot esta completamente vertical.

Cuando:

```text
theta > 0
```

el robot esta inclinado hacia un lado.

Cuando:

```text
theta < 0
```

el robot esta inclinado hacia el lado contrario.

El controlador debe generar una aceleracion de la base para compensar la caida del cuerpo.

De forma simplificada, la dinamica usada por la simulacion es:

```text
theta_ddot = (g / L) * sin(theta) - (x_ddot / L) * cos(theta) - damping * theta_dot
```

Donde:

- `theta` es el angulo de inclinacion.
- `theta_dot` es la velocidad angular.
- `theta_ddot` es la aceleracion angular.
- `g` es la gravedad.
- `L` es la altura aproximada del centro de masa.
- `x_ddot` es la aceleracion horizontal de la base.
- `damping` representa perdidas o amortiguamiento.

Este modelo no busca reemplazar al robot real, sino servir como una herramienta pedagogica para entender el control.

## 5. Controlador PID clasico

El controlador PID clasico usa tres terminos:

```text
u = Kp * error + Ki * integral(error) + Kd * derivative(error)
```

Donde:

- `Kp` es la ganancia proporcional.
- `Ki` es la ganancia integral.
- `Kd` es la ganancia derivativa.
- `u` es la senal de control.

En el caso del robot auto-balanceado, el error principal esta relacionado con la inclinacion:

```text
error = theta - theta_objetivo
```

El PID intenta que el angulo del robot se mantenga cerca de cero grados.

### Interpretacion de cada termino

**Termino proporcional (`Kp`)**

Responde al error actual. Si el robot esta muy inclinado, el controlador genera una accion mas fuerte.

**Termino integral (`Ki`)**

Acumula errores pasados. Sirve para corregir errores persistentes, pero si se usa demasiado puede causar oscilaciones o saturacion.

**Termino derivativo (`Kd`)**

Responde a la velocidad del cambio. Ayuda a frenar el movimiento antes de que el robot se pase del punto de equilibrio.

## 6. PID potenciado por IA

En esta practica, el PID potenciado por IA no reemplaza completamente al PID. En lugar de eso, usa una capa inteligente para ajustar las ganancias del controlador segun el estado actual del robot.

La idea es que el robot no necesita comportarse igual en todas las situaciones. Por ejemplo:

- Si esta casi vertical, puede usar ganancias suaves.
- Si se esta cayendo rapidamente, necesita ganancias mas agresivas.
- Si se esta desplazando demasiado, necesita corregir la deriva de posicion.

Para esto se usa una **mezcla de expertos**.

## 7. Mezcla de expertos

La mezcla de expertos consiste en tener varios controladores o configuraciones especializadas y combinar sus salidas segun la situacion.

En la simulacion se usan tres expertos:

### Experto 1: Balance

Trabaja cuando el robot esta cerca de la vertical. Su objetivo es mantener el equilibrio con movimientos suaves.

### Experto 2: Recuperacion

Trabaja cuando el robot tiene una inclinacion grande o una velocidad angular alta. Su objetivo es evitar la caida.

### Experto 3: Deriva

Trabaja cuando el robot se ha desplazado demasiado de su posicion inicial. Su objetivo es reducir el desplazamiento acumulado.

La capa de IA calcula pesos para cada experto:

```text
peso_balance + peso_recuperacion + peso_deriva = 1
```

Luego combina las ganancias:

```text
Kp_final = peso_balance * Kp_balance + peso_recuperacion * Kp_recuperacion + peso_deriva * Kp_deriva
```

Lo mismo ocurre para `Ki` y `Kd`.

Este enfoque se puede considerar una forma inicial de IA porque el controlador adapta su comportamiento segun el estado del sistema. En trabajos futuros, estos pesos podrian ser aprendidos por una red neuronal, logica difusa, aprendizaje por refuerzo o algoritmos geneticos.

## 8. Archivos del proyecto

El simulador 2D esta en:

```text
scripts/sim_2d_pid_ai.py
```

Al ejecutarlo, genera dos archivos:

```text
data/sim_2d/pid_vs_pid_ai_2d.csv
data/sim_2d/pid_vs_pid_ai_2d.html
```

El archivo CSV contiene los datos numericos de la simulacion.

El archivo HTML contiene graficas para analizar visualmente el comportamiento del robot.

## 9. Como ejecutar la simulacion

Desde la carpeta del proyecto:

```powershell
cd D:\PercetptIA\Self_Balancing_Robot
python scripts\sim_2d_pid_ai.py
```

Tambien se puede modificar el escenario inicial:

```powershell
python scripts\sim_2d_pid_ai.py --initial-tilt-deg 10 --impulse-accel -3.0 --duration 15
```

Parametros utiles:

- `--initial-tilt-deg`: inclinacion inicial del robot.
- `--impulse-accel`: perturbacion externa aplicada al robot.
- `--duration`: duracion total de la simulacion.
- `--dt`: paso de integracion numerica.

## 10. Variables registradas en el CSV

Las columnas principales son:

| Variable | Descripcion |
|---|---|
| `controller` | Nombre del controlador usado. |
| `time_s` | Tiempo de simulacion en segundos. |
| `tilt_deg` | Inclinacion del robot en grados. |
| `tilt_rate_deg_s` | Velocidad angular del robot. |
| `x_m` | Posicion horizontal de la base. |
| `x_dot_m_s` | Velocidad horizontal de la base. |
| `command_accel_m_s2` | Aceleracion ordenada por el controlador. |
| `command_motor_rpm` | RPM equivalente del motor. |
| `kp`, `ki`, `kd` | Ganancias usadas por el controlador. |
| `expert_balance` | Peso del experto de balance. |
| `expert_recovery` | Peso del experto de recuperacion. |
| `expert_drift` | Peso del experto de deriva. |

## 11. Metricas de comparacion

Para comparar los controladores se usan varias metricas.

### Maxima inclinacion

Indica el mayor angulo alcanzado por el robot durante la simulacion. Mientras menor sea, mejor.

```text
max_tilt = max(abs(theta))
```

### Error absoluto integrado

Mide cuanto error angular se acumulo durante toda la simulacion.

```text
IAE = integral(abs(theta)) dt
```

Un valor menor indica mejor control general.

### RPM maxima

Indica el maximo esfuerzo aproximado que se pide a los motores.

Un controlador puede tener mejor equilibrio, pero si exige demasiadas RPM puede ser poco realista para el robot fisico.

### Tiempo de caida

Si el robot supera un angulo limite, se considera que cayo. En esta simulacion el limite se define alrededor de 45 grados.

## 12. Resultado de referencia

Con los parametros actuales, la simulacion produce aproximadamente:

| Controlador | Estado | Max tilt | IAE | RPM max |
|---|---:|---:|---:|---:|
| PID normal | No cae | 15.95 deg | 1.5025 | 100.9 |
| PID IA | No cae | 14.64 deg | 1.3484 | 133.3 |

La interpretacion es que el PID potenciado por IA logra reducir el error acumulado y la inclinacion maxima, aunque usa un mayor esfuerzo de motor.

Esto muestra una idea importante en control: no siempre existe una mejora gratis. Muchas veces se mejora estabilidad a cambio de mayor energia, velocidad o exigencia sobre los actuadores.

## 13. Actividad sugerida para estudiantes

### Actividad 1: Observar el comportamiento base

1. Ejecutar la simulacion con los parametros por defecto.
2. Abrir el archivo HTML generado.
3. Comparar la curva de inclinacion del PID normal y del PID IA.
4. Identificar cual controlador reduce mejor el angulo.

### Actividad 2: Cambiar la inclinacion inicial

Ejecutar:

```powershell
python scripts\sim_2d_pid_ai.py --initial-tilt-deg 3
python scripts\sim_2d_pid_ai.py --initial-tilt-deg 10
python scripts\sim_2d_pid_ai.py --initial-tilt-deg 15
```

Preguntas:

- Que controlador resiste mejor inclinaciones grandes?
- En que momento empieza a saturarse el motor?
- El controlador IA siempre mejora al PID clasico?

### Actividad 3: Cambiar la perturbacion externa

Ejecutar:

```powershell
python scripts\sim_2d_pid_ai.py --impulse-accel -1.0
python scripts\sim_2d_pid_ai.py --impulse-accel -3.0
python scripts\sim_2d_pid_ai.py --impulse-accel -5.0
```

Preguntas:

- Que ocurre cuando el golpe externo es mas fuerte?
- El experto de recuperacion aumenta su peso?
- Que pasa con las RPM?

### Actividad 4: Analizar el CSV

Abrir el archivo:

```text
data/sim_2d/pid_vs_pid_ai_2d.csv
```

Buscar las columnas:

```text
kp, ki, kd, expert_balance, expert_recovery, expert_drift
```

Preguntas:

- Las ganancias del PID IA permanecen constantes?
- En que momento aumenta el experto de recuperacion?
- En que momento aumenta el experto de deriva?

## 14. Discusion tecnica

El modelo 2D permite entender la logica del control sin depender de Gazebo. Sin embargo, tiene limitaciones:

- No modela completamente la friccion de las ruedas.
- No incluye flexibilidad mecanica.
- No simula ruido realista de sensores de forma completa.
- No incluye geometria 3D ni colisiones complejas.
- No representa exactamente el comportamiento de motores reales.

Aun asi, es muy util como primer banco de pruebas. Si una idea de control no funciona en 2D, probablemente tampoco funcionara bien en 3D. Si funciona en 2D, entonces puede pasar a una validacion mas exigente en Gazebo.

## 15. Relacion con Gazebo y el robot fisico

El flujo recomendado del proyecto es:

```text
Modelo teorico 2D -> Simulacion Gazebo 3D -> Robot fisico real
```

Primero se prueba el controlador en 2D para verificar la idea.

Luego se lleva a Gazebo para probar geometria, sensores, masa, ruedas, friccion y colisiones.

Finalmente, cuando el comportamiento sea seguro, se prueba en el robot fisico con limites conservadores de motor.

## 16. Conclusiones

1. Un robot auto-balanceado puede estudiarse inicialmente como un pendulo invertido en 2D.
2. El PID clasico es una buena base para entender el control del equilibrio.
3. Un PID potenciado por IA puede adaptar sus ganancias segun la situacion del robot.
4. La mezcla de expertos permite combinar comportamientos especializados: balance, recuperacion y correccion de deriva.
5. La mejora del control debe evaluarse junto con el esfuerzo de motor, no solo con el error angular.
6. La simulacion 2D es una etapa educativa y tecnica importante antes de pasar a Gazebo o al robot real.

## 17. Preguntas de reflexion

1. Por que un robot auto-balanceado se parece a un pendulo invertido?
2. Que efecto tiene aumentar `Kp`?
3. Por que un valor alto de `Ki` puede ser peligroso?
4. Que ventaja tiene ajustar las ganancias del PID durante la simulacion?
5. En que casos el PID IA podria ser peor que el PID clasico?
6. Por que es importante limitar las RPM del motor?
7. Que diferencias esperarias al pasar del modelo 2D a Gazebo 3D?

## 18. Trabajo futuro

Como extension del proyecto, se pueden implementar:

- Entrenamiento de una red neuronal para escoger las ganancias del PID.
- Control difuso para reemplazar la mezcla de expertos manual.
- Optimizacion automatica de `Kp`, `Ki` y `Kd` mediante algoritmos geneticos.
- Comparacion con control LQR.
- Exportacion de datasets para entrenar modelos de IA.
- Validacion del mismo controlador en Gazebo.
- Pruebas finales en el robot fisico con limites de seguridad.
## 19. Animacion de estabilizacion

Ademas de las graficas, el proyecto incluye una animacion HTML que muestra el comportamiento del robot en el tiempo. La animacion compara lado a lado el PID normal y el PID potenciado por IA.

Para generarla:

```powershell
python scripts\create_2d_animation.py
```

El archivo resultante es:

```text
data/sim_2d/pid_vs_pid_ai_2d_animation.html
```

La animacion permite observar visualmente:

- Como cambia la inclinacion del cuerpo.
- Como se desplaza la base del robot.
- Que controlador usa mayor esfuerzo de motor.
- Cuando aumenta el experto de recuperacion del PID IA.

Esta visualizacion ayuda a conectar las curvas numericas con el movimiento fisico esperado del robot.
## 20. Compendio HTML recomendado

Para clase se recomienda usar el compendio en un solo archivo HTML. Este documento integra guia teorica, metricas, graficas, animacion y actividades.

Para generarlo:

```powershell
python scripts/create_2d_compendium.py
```

Archivo resultante:

```text
data/sim_2d/guia_compendio_pid_ia_2d.html
```
## 21. Teoria ampliada para interpretar la simulacion

### 21.1 Por que el robot es un pendulo invertido

Un robot auto-balanceado de dos ruedas es inestable por naturaleza. Esto significa que la posicion vertical no es una posicion de reposo segura; es una posicion que debe corregirse continuamente. Si el cuerpo se inclina aunque sea un poco, el centro de masa deja de estar alineado con el eje de las ruedas y la gravedad genera un torque que aumenta la caida.

La comparacion con un pendulo invertido ayuda porque el cuerpo del robot se parece a una barra que intenta caer, mientras que las ruedas actuan como una base movil. El controlador no empuja directamente el cuerpo del robot; lo que hace es mover las ruedas para colocar de nuevo la base debajo del centro de masa.

La idea fisica principal es:

```text
si el cuerpo se inclina -> mover la base para recuperar el centro de masa
```

Por eso el sentido del comando de motor es tan importante. Si las ruedas aceleran hacia el lado equivocado, el robot no se recupera; al contrario, se cae mas rapido.

### 21.2 Que representa la perturbacion

En la simulacion se aplica una perturbacion en un instante definido, por defecto:

```text
t = 4.0 s
```

Esta perturbacion representa un golpe, empuje o cambio externo que intenta sacar al robot de su equilibrio. En las graficas se marca con una linea vertical para que el estudiante pueda separar tres momentos:

- Antes de la perturbacion: el controlador intenta mantener el robot estable.
- Durante la perturbacion: el sistema recibe un cambio brusco.
- Despues de la perturbacion: se observa si el controlador se recupera o si el error sigue creciendo.

Una buena respuesta no significa que la curva no se mueva. Una buena respuesta significa que, despues del golpe, el robot reduce el error, evita la caida y vuelve hacia una region cercana al equilibrio.

### 21.3 Como interpretar la deriva

La posicion horizontal `x` indica hacia que lado se desplaza la base del robot. Puede ser positiva o negativa. Sin embargo, para saber si el robot esta cerca o lejos del punto inicial, conviene observar la magnitud:

```text
|x| = distancia al origen sin importar el lado
```

Por eso se agrego la grafica de magnitud de deriva `|x|`. Si `|x|` baja despues de la perturbacion, significa que el robot esta regresando hacia el origen. Si `|x|` crece, significa que el robot se esta alejando cada vez mas.

En los resultados actuales, el PID potenciado por IA termina con menor `|x|` final que el PID normal. Eso permite decir que, ademas de mejorar el error angular, tambien deja al robot mas cerca del punto de partida.

### 21.4 Que significa que el PID IA mejore

La mejora del PID IA debe analizarse con varias metricas al mismo tiempo:

- Menor inclinacion maxima: el cuerpo se aleja menos de la vertical.
- Menor error acumulado: el robot pasa mas tiempo cerca del objetivo.
- Menor `|x|` final: termina mas cerca del origen.
- Mayor RPM maxima: puede requerir mas esfuerzo del motor.

Esto es importante porque en control casi nunca existe una mejora gratuita. Un controlador puede verse mejor porque corrige mas rapido, pero esa correccion puede exigir mas energia o mas velocidad de motor. En un robot fisico real, ese costo debe revisarse con cuidado para no saturar los motores ni volver insegura la prueba.

### 21.5 Lectura recomendada de las graficas

Para analizar cada grafica, se recomienda seguir este orden:

1. Ubicar la linea vertical de perturbacion.
2. Observar que ocurre justo despues del golpe.
3. Comparar la curva azul del PID normal con la curva roja del PID IA.
4. Revisar si la curva se acerca a cero o si se aleja.
5. Confirmar la interpretacion con las metricas numericas.

La conclusion no debe basarse solo en una imagen. Debe justificarse usando la animacion, las curvas y la tabla de metricas.
