# Requirements Document: pygame-rl-simulacion

## Introduction

Este documento define los requisitos funcionales y no funcionales para el entorno de simulación 2D con aprendizaje por refuerzo en Pygame. Los requisitos se derivan del diseño técnico y cubren el entorno de simulación, los agentes de RL, el sistema de visualización, la persistencia de modelos y la interfaz de usuario.

---

## Requirements

### 1. Entorno de Simulación 2D

#### 1.1 Mundo y Renderizado

**User Story**: Como desarrollador, quiero un mundo 2D renderizado con Pygame con pantalla fija, para poder visualizar el aprendizaje del agente en tiempo real.

**Acceptance Criteria**:

- [ ] 1.1.1 El entorno renderiza un mundo 2D de tamaño configurable (por defecto 800×600 píxeles) usando Pygame.
- [ ] 1.1.2 El mundo está dividido en una cuadrícula de celdas de tamaño configurable (por defecto 40×40 píxeles).
- [ ] 1.1.3 El entorno soporta tres modos de renderizado: `"human"` (ventana visible a velocidad normal), `"fast"` (ventana visible a máxima velocidad), y `"headless"` (sin ventana, para entrenamiento puro).
- [ ] 1.1.4 En modo `"human"` y `"fast"`, el entorno muestra el agente, obstáculos, recursos y enemigos con sprites o formas geométricas diferenciadas por color.
- [ ] 1.1.5 El entorno expone la interfaz Gymnasium: `reset()`, `step(action)`, `render()`, `close()`.

#### 1.2 Obstáculos

**User Story**: Como desarrollador, quiero obstáculos estáticos y dinámicos en el mundo, para que el agente aprenda a navegar en un entorno no trivial.

**Acceptance Criteria**:

- [ ] 1.2.1 El mundo contiene obstáculos estáticos (paredes, rocas) generados aleatoriamente al inicio de cada episodio, con cantidad configurable (por defecto 15).
- [ ] 1.2.2 Los obstáculos estáticos son impenetrables: el agente no puede moverse a una celda ocupada por un obstáculo.
- [ ] 1.2.3 El mundo contiene enemigos dinámicos que se mueven aleatoriamente o con un patrón simple, con cantidad configurable (por defecto 3).
- [ ] 1.2.4 El contacto del agente con un enemigo termina el episodio con recompensa de muerte (`REWARD_DEATH = -10.0`).
- [ ] 1.2.5 Los enemigos no atraviesan obstáculos estáticos.

#### 1.3 Recursos y Objetivos

**User Story**: Como desarrollador, quiero múltiples recursos recolectables en el mundo, para que el agente tenga objetivos positivos que aprender a alcanzar.

**Acceptance Criteria**:

- [ ] 1.3.1 El mundo contiene recursos recolectables (ítems) generados aleatoriamente, con cantidad configurable (por defecto 5).
- [ ] 1.3.2 Cuando el agente se mueve a la celda de un recurso, el recurso desaparece y el agente recibe recompensa positiva (`REWARD_COLLECT = +5.0`).
- [ ] 1.3.3 El episodio termina exitosamente cuando el agente recolecta todos los recursos del mundo.
- [ ] 1.3.4 El sistema registra si el episodio terminó con éxito (`success=True`) o por muerte/timeout.

#### 1.4 Sistema de Recompensas

**User Story**: Como investigador de RL, quiero un sistema de recompensas configurable y bien definido, para poder ajustar el comportamiento del agente.

**Acceptance Criteria**:

- [ ] 1.4.1 Las recompensas están definidas como constantes configurables: `REWARD_COLLECT=+5.0`, `REWARD_EXPLORE=+0.5`, `REWARD_COLLISION=-1.0`, `REWARD_DEATH=-10.0`, `REWARD_STEP=-0.01`.
- [ ] 1.4.2 El agente recibe `REWARD_EXPLORE` al visitar por primera vez una celda del mapa en el episodio actual.
- [ ] 1.4.3 El agente recibe `REWARD_COLLISION` al intentar moverse a una celda con obstáculo (la posición no cambia).
- [ ] 1.4.4 El agente recibe `REWARD_STEP` en cada paso para incentivar eficiencia.
- [ ] 1.4.5 El episodio termina con `done=True` si se supera `max_steps_per_episode` (por defecto 500).

---

### 2. Agente Q-Learning (Fase 1)

#### 2.1 Tabla Q y Política

**User Story**: Como investigador de RL, quiero un agente Q-Learning clásico con tabla de estados discretizados, para establecer una línea base de aprendizaje.

**Acceptance Criteria**:

- [ ] 2.1.1 El agente mantiene una tabla Q implementada como `defaultdict` donde las claves son tuplas de estado discreto y los valores son arrays de Q-values por acción.
- [ ] 2.1.2 El agente soporta exactamente 4 acciones: arriba (0), abajo (1), izquierda (2), derecha (3).
- [ ] 2.1.3 El estado discreto es una tupla de 8 enteros: posición en grid (x, y), tipo de celda en las 4 direcciones adyacentes, presencia de recurso en radio, presencia de enemigo en radio.
- [ ] 2.1.4 La actualización de Q-values usa la ecuación de Bellman: `Q(s,a) ← Q(s,a) + α(r + γ·max Q(s',a') - Q(s,a))`.
- [ ] 2.1.5 Los hiperparámetros `alpha` (tasa de aprendizaje), `gamma` (factor de descuento) son configurables.

#### 2.2 Exploración Epsilon-Greedy

**User Story**: Como investigador de RL, quiero exploración epsilon-greedy con decaimiento, para que el agente explore al inicio y explote al final del entrenamiento.

**Acceptance Criteria**:

- [ ] 2.2.1 El agente implementa política epsilon-greedy: con probabilidad `epsilon` elige acción aleatoria, con probabilidad `1-epsilon` elige `argmax(Q(s,·))`.
- [ ] 2.2.2 `epsilon` decae multiplicativamente después de cada episodio: `epsilon = max(epsilon_min, epsilon * epsilon_decay)`.
- [ ] 2.2.3 Los valores `epsilon_start`, `epsilon_min`, `epsilon_decay` son configurables.
- [ ] 2.2.4 `epsilon` nunca cae por debajo de `epsilon_min`.

#### 2.3 Persistencia Q-Table

**User Story**: Como usuario, quiero guardar y cargar la Q-table entrenada, para no tener que reentrenar desde cero.

**Acceptance Criteria**:

- [ ] 2.3.1 El agente puede guardar la Q-table completa en formato JSON en una ruta especificada.
- [ ] 2.3.2 El agente puede cargar una Q-table desde un archivo JSON y continuar entrenando o ejecutar en modo demo.
- [ ] 2.3.3 Si el archivo de carga no existe o está corrupto, el agente inicia con tabla vacía y registra un warning.

---

### 3. Agente DQN (Fase 2)

#### 3.1 Red Neuronal

**User Story**: Como investigador de RL, quiero un agente DQN con red neuronal en PyTorch, para escalar el aprendizaje a espacios de estado continuos.

**Acceptance Criteria**:

- [ ] 3.1.1 La red neuronal es un MLP (Multi-Layer Perceptron) con arquitectura configurable: input_dim → hidden_dim → hidden_dim → num_actions.
- [ ] 3.1.2 La red usa activaciones ReLU en capas ocultas y sin activación en la capa de salida.
- [ ] 3.1.3 El agente mantiene dos redes: la red principal (online) y la target network con los mismos pesos iniciales.
- [ ] 3.1.4 La target network se actualiza copiando los pesos de la red principal cada `target_update_freq` pasos.
- [ ] 3.1.5 Si PyTorch no está instalado, el sistema lanza `ImportError` con mensaje claro indicando que DQN requiere PyTorch.

#### 3.2 Experience Replay

**User Story**: Como investigador de RL, quiero un replay buffer para el DQN, para estabilizar el entrenamiento rompiendo la correlación entre transiciones consecutivas.

**Acceptance Criteria**:

- [ ] 3.2.1 El replay buffer almacena transiciones `(state, action, reward, next_state, done)` con capacidad máxima configurable (por defecto 10,000).
- [ ] 3.2.2 Cuando el buffer está lleno, las transiciones más antiguas son descartadas (FIFO).
- [ ] 3.2.3 El buffer puede samplear un batch aleatorio de tamaño `batch_size` de forma uniforme.
- [ ] 3.2.4 El entrenamiento de la red solo comienza cuando el buffer tiene al menos `batch_size` transiciones.

#### 3.3 Entrenamiento DQN

**User Story**: Como investigador de RL, quiero que el DQN use la ecuación de Bellman con la target network, para un entrenamiento estable.

**Acceptance Criteria**:

- [ ] 3.3.1 El loss se calcula como MSE entre Q-values predichos por la red principal y los targets calculados con la target network: `target = r + γ · max_a' Q_target(s', a') · (1 - done)`.
- [ ] 3.3.2 El optimizador es Adam con tasa de aprendizaje configurable (por defecto `1e-3`).
- [ ] 3.3.3 El agente aplica gradient clipping con norma máxima configurable para evitar explosión de gradientes.

#### 3.4 Persistencia DQN

**User Story**: Como usuario, quiero guardar y cargar el modelo DQN entrenado, para reutilizarlo en modo demo.

**Acceptance Criteria**:

- [ ] 3.4.1 El agente guarda los pesos de la red principal en formato `.pt` usando `torch.save`.
- [ ] 3.4.2 El agente carga pesos desde `.pt` usando `torch.load(..., weights_only=True)`.
- [ ] 3.4.3 Si el archivo no existe o la arquitectura no coincide, el agente inicia con pesos aleatorios y registra un warning.

---

### 4. Visualización en Tiempo Real

#### 4.1 Heatmap de Q-Values

**User Story**: Como investigador de RL, quiero ver un heatmap de Q-values sobre el mapa, para entender qué ha aprendido el agente sobre cada zona del mundo.

**Acceptance Criteria**:

- [ ] 4.1.1 El visualizador puede renderizar un heatmap sobre el mapa del mundo mostrando el valor máximo de Q para cada celda visitada.
- [ ] 4.1.2 El heatmap usa una escala de colores (frío→caliente) donde colores cálidos indican Q-values altos.
- [ ] 4.1.3 El heatmap se actualiza en tiempo real durante el entrenamiento.
- [ ] 4.1.4 El heatmap solo está disponible en modo Q-Learning (no aplica a DQN directamente).

#### 4.2 Curva de Aprendizaje

**User Story**: Como investigador de RL, quiero ver la curva de recompensa acumulada por episodio, para monitorear el progreso del aprendizaje.

**Acceptance Criteria**:

- [ ] 4.2.1 El visualizador muestra una gráfica de línea con la recompensa total por episodio en un panel lateral o ventana secundaria.
- [ ] 4.2.2 La curva se actualiza al final de cada episodio.
- [ ] 4.2.3 La curva muestra una media móvil de los últimos 50 episodios superpuesta sobre los valores individuales.

#### 4.3 Overlay de Estadísticas

**User Story**: Como usuario, quiero ver estadísticas en tiempo real en la pantalla, para monitorear el estado del entrenamiento sin salir de la ventana.

**Acceptance Criteria**:

- [ ] 4.3.1 La pantalla muestra en todo momento: número de episodio actual, epsilon actual, recompensa del episodio actual, pasos del episodio actual.
- [ ] 4.3.2 Al final de cada episodio se muestra brevemente si fue exitoso o no.
- [ ] 4.3.3 El overlay no interfiere con la visualización del mundo (se renderiza en un área dedicada o con transparencia).

---

### 5. Modos de Ejecución

#### 5.1 Modo Entrenamiento

**User Story**: Como investigador de RL, quiero un modo de entrenamiento con velocidad configurable, para entrenar rápidamente sin esperar el renderizado.

**Acceptance Criteria**:

- [ ] 5.1.1 El modo `"headless"` ejecuta el loop de entrenamiento sin inicializar la ventana de Pygame, maximizando la velocidad.
- [ ] 5.1.2 El modo `"fast"` renderiza la ventana pero sin límite de FPS (sin `pygame.time.Clock.tick()`).
- [ ] 5.1.3 El número de episodios de entrenamiento es configurable por línea de comandos o archivo de configuración.
- [ ] 5.1.4 El sistema guarda automáticamente el modelo cada N episodios configurables (checkpoint).

#### 5.2 Modo Demo

**User Story**: Como usuario, quiero un modo demo donde pueda ver al agente entrenado actuar, para evaluar visualmente el resultado del entrenamiento.

**Acceptance Criteria**:

- [ ] 5.2.1 El modo demo carga un modelo guardado (Q-table JSON o DQN .pt) y ejecuta el agente con `epsilon=0.0` (sin exploración).
- [ ] 5.2.2 El modo demo renderiza a velocidad normal (60 FPS) con todos los elementos visuales activos.
- [ ] 5.2.3 El modo demo puede ejecutarse desde línea de comandos: `python main.py --mode demo --model models/q_table.json`.
- [ ] 5.2.4 El modo demo muestra el overlay de estadísticas en tiempo real.

---

### 6. Estadísticas y Persistencia

#### 6.1 Registro de Métricas

**User Story**: Como investigador de RL, quiero que el sistema registre métricas detalladas por episodio, para analizar el progreso del entrenamiento.

**Acceptance Criteria**:

- [ ] 6.1.1 El sistema registra por episodio: número de episodio, recompensa total, número de pasos, si fue exitoso, epsilon actual, loss promedio (solo DQN).
- [ ] 6.1.2 Las métricas se pueden exportar a CSV al finalizar el entrenamiento.
- [ ] 6.1.3 El sistema calcula y muestra la tasa de éxito de los últimos 100 episodios.

#### 6.2 Guardado de Modelos

**User Story**: Como usuario, quiero guardar y cargar modelos entrenados fácilmente, para continuar el entrenamiento o ejecutar demos.

**Acceptance Criteria**:

- [ ] 6.2.1 Los modelos se guardan en el directorio `models/` por defecto, con nombre configurable.
- [ ] 6.2.2 El guardado automático ocurre cada N episodios (configurable, por defecto 100) y al finalizar el entrenamiento.
- [ ] 6.2.3 El sistema puede cargar un modelo y continuar el entrenamiento desde donde se dejó (incluyendo epsilon actual).
- [ ] 6.2.4 Los archivos de modelo incluyen metadatos: tipo de agente, hiperparámetros, número de episodios entrenados.

---

### 7. Interfaz de Línea de Comandos

**User Story**: Como usuario, quiero controlar el sistema desde la línea de comandos, para cambiar entre modos y configuraciones sin editar código.

**Acceptance Criteria**:

- [ ] 7.1 El script principal acepta `--mode` con valores: `train`, `demo`, `continue`.
- [ ] 7.2 El script acepta `--agent` con valores: `qlearning`, `dqn`.
- [ ] 7.3 El script acepta `--model` para especificar la ruta del modelo a cargar/guardar.
- [ ] 7.4 El script acepta `--episodes` para especificar el número de episodios de entrenamiento.
- [ ] 7.5 El script acepta `--render` con valores: `human`, `fast`, `headless`.
- [ ] 7.6 Ejecutar `python main.py --help` muestra la ayuda completa con todos los argumentos disponibles.

---

### 8. Compatibilidad y Extensibilidad

**User Story**: Como desarrollador, quiero que el entorno sea compatible con Gymnasium, para poder usar Stable-Baselines3 en el futuro.

**Acceptance Criteria**:

- [ ] 8.1 La clase `Environment` implementa los métodos `reset()`, `step()`, `render()`, `close()` con las firmas exactas de Gymnasium.
- [ ] 8.2 `reset()` retorna `(observation, info)` compatible con Gymnasium v0.26+.
- [ ] 8.3 `step()` retorna `(observation, reward, terminated, truncated, info)` compatible con Gymnasium v0.26+.
- [ ] 8.4 El entorno define `observation_space` y `action_space` como atributos de instancia usando tipos de Gymnasium (`spaces.Box`, `spaces.Discrete`).
- [ ] 8.5 La clase `BaseAgent` define la interfaz común que tanto `QAgent` como `DQNAgent` implementan, facilitando el intercambio de agentes.
