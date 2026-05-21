# Tasks: pygame-rl-simulacion

## Implementation Plan

### Phase 1: Scaffolding y Configuración Base

- [-] 1. Crear estructura de directorios del proyecto
  - [x] 1.1 Crear directorios: `environment/`, `agents/`, `visualization/`, `utils/`, `models/`, `tests/`
  - [x] 1.2 Crear archivos `__init__.py` en cada paquete
  - [x] 1.3 Crear `requirements.txt` con dependencias: pygame, numpy, torch (opcional), hypothesis, pytest
  - [x] 1.4 Crear `config.py` con todas las constantes y dataclasses de configuración (`WorldConfig`, `QLearningConfig`, `DQNConfig`, constantes de recompensa)

### Phase 2: Entorno de Simulación

- [ ] 2. Implementar el mundo base (`environment/world.py`)
  - [ ] 2.1 Implementar clase `World` con cuadrícula de celdas y generación aleatoria de obstáculos
  - [ ] 2.2 Implementar detección de colisiones con obstáculos y bordes del mundo
  - [ ] 2.3 Implementar sistema de celdas visitadas para recompensa de exploración

- [ ] 3. Implementar sprites y entidades (`environment/sprites.py`, `obstacles.py`, `collectibles.py`, `enemies.py`)
  - [ ] 3.1 Implementar `AgentSprite` con posición, movimiento en 4 direcciones y radio de visión
  - [ ] 3.2 Implementar `ObstacleManager` con generación y renderizado de obstáculos estáticos
  - [ ] 3.3 Implementar `CollectibleManager` con recursos recolectables y detección de colección
  - [ ] 3.4 Implementar `EnemyManager` con movimiento aleatorio de enemigos y detección de contacto

- [ ] 4. Implementar entorno principal (`environment/pygame_env.py`)
  - [ ] 4.1 Implementar clase `PygameEnvironment` con interfaz Gymnasium v0.26+ (`reset`, `step`, `render`, `close`)
  - [ ] 4.2 Implementar `observation_space` (Box) y `action_space` (Discrete(4))
  - [ ] 4.3 Implementar `_get_discrete_state()` para Q-Learning (tupla de 8 enteros)
  - [ ] 4.4 Implementar `_get_continuous_state()` para DQN (vector float32 de 12 dimensiones)
  - [ ] 4.5 Implementar `_calculate_reward()` con todas las recompensas definidas en config
  - [ ] 4.6 Implementar los tres modos de renderizado: `human`, `fast`, `headless`

### Phase 3: Agente Q-Learning

- [ ] 5. Implementar Q-table (`agents/q_table.py`)
  - [ ] 5.1 Implementar `QTable` como wrapper de `defaultdict` con inicialización de ceros y métodos `get`, `update`, `max_value`

- [ ] 6. Implementar agente Q-Learning (`agents/q_agent.py`)
  - [ ] 6.1 Implementar clase `QAgent` heredando de `BaseAgent`
  - [ ] 6.2 Implementar `select_action(state, epsilon)` con política epsilon-greedy
  - [ ] 6.3 Implementar `learn(state, action, reward, next_state, done)` con ecuación de Bellman
  - [ ] 6.4 Implementar `decay_epsilon()` con decaimiento multiplicativo
  - [ ] 6.5 Implementar `save_model(path)` serializando Q-table a JSON
  - [ ] 6.6 Implementar `load_model(path)` deserializando Q-table desde JSON con manejo de errores

### Phase 4: Agente DQN

- [ ] 7. Implementar red neuronal (`agents/dqn_network.py`)
  - [ ] 7.1 Implementar clase `DQNNetwork` (MLP) con arquitectura configurable: input → hidden → hidden → output
  - [ ] 7.2 Usar activaciones ReLU en capas ocultas, sin activación en capa de salida

- [ ] 8. Implementar replay buffer (`agents/replay_buffer.py`)
  - [ ] 8.1 Implementar `ReplayBuffer` con `deque(maxlen=capacity)` para almacenar `Transition`
  - [ ] 8.2 Implementar `push(state, action, reward, next_state, done)`
  - [ ] 8.3 Implementar `sample(batch_size)` retornando tensores PyTorch listos para entrenamiento

- [ ] 9. Implementar agente DQN (`agents/dqn_agent.py`)
  - [ ] 9.1 Implementar clase `DQNAgent` heredando de `BaseAgent` con detección de disponibilidad de PyTorch
  - [ ] 9.2 Implementar red principal y target network con mismos pesos iniciales
  - [ ] 9.3 Implementar `select_action(state, epsilon)` usando la red principal
  - [ ] 9.4 Implementar `learn(...)` con: push a buffer, sample batch, calcular targets con target network, MSE loss, backprop, gradient clipping
  - [ ] 9.5 Implementar `update_target_network()` copiando pesos de red principal a target
  - [ ] 9.6 Implementar `save_model(path)` con `torch.save` y metadatos
  - [ ] 9.7 Implementar `load_model(path)` con `torch.load(..., weights_only=True)` y manejo de errores

- [ ] 10. Implementar interfaz base (`agents/base_agent.py`)
  - [ ] 10.1 Implementar clase abstracta `BaseAgent` con métodos abstractos: `select_action`, `learn`, `decay_epsilon`, `save_model`, `load_model`

### Phase 5: Visualización

- [ ] 11. Implementar heatmap de Q-values (`visualization/heatmap.py`)
  - [ ] 11.1 Implementar `HeatmapRenderer` que dibuja sobre el mapa una capa semitransparente con colores según Q-value máximo por celda
  - [ ] 11.2 Implementar escala de colores frío (azul) → caliente (rojo) normalizada al rango actual de Q-values

- [ ] 12. Implementar curva de aprendizaje (`visualization/curves.py`)
  - [ ] 12.1 Implementar `LearningCurveRenderer` que dibuja la recompensa por episodio en un panel lateral
  - [ ] 12.2 Añadir media móvil de 50 episodios superpuesta sobre los valores individuales

- [ ] 13. Implementar visualizador principal (`visualization/visualizer.py`)
  - [ ] 13.1 Implementar clase `Visualizer` que orquesta `HeatmapRenderer`, `LearningCurveRenderer` y el overlay de estadísticas
  - [ ] 13.2 Implementar `render_stats_overlay(stats)` mostrando episodio, epsilon, recompensa, pasos en área dedicada

### Phase 6: Utilidades

- [ ] 14. Implementar tracker de estadísticas (`utils/stats.py`)
  - [ ] 14.1 Implementar `StatsTracker` con `record_step(reward)`, `end_episode()`, `get_history()`
  - [ ] 14.2 Implementar cálculo de tasa de éxito de los últimos 100 episodios
  - [ ] 14.3 Implementar `save_csv(path)` exportando historial completo

- [ ] 15. Implementar I/O de modelos (`utils/model_io.py`)
  - [ ] 15.1 Implementar `save_qtable_json(q_table, path, metadata)` con metadatos (hiperparámetros, episodios)
  - [ ] 15.2 Implementar `load_qtable_json(path)` con manejo de errores y retorno de metadatos
  - [ ] 15.3 Implementar `save_dqn_pt(network, path, metadata)` usando `torch.save`
  - [ ] 15.4 Implementar `load_dqn_pt(path)` usando `torch.load(..., weights_only=True)`
  - [ ] 15.5 Implementar `load_agent(path, agent_type)` como función de conveniencia para modo demo

### Phase 7: Game Loop y Entry Point

- [ ] 16. Implementar game loop (`main.py`)
  - [ ] 16.1 Implementar parser de argumentos CLI con: `--mode`, `--agent`, `--model`, `--episodes`, `--render`
  - [ ] 16.2 Implementar `run_training(env, agent, stats, visualizer, config)` con loop de episodios, guardado de checkpoints y manejo de `pygame.QUIT`
  - [ ] 16.3 Implementar `run_demo(env, agent)` con `epsilon=0.0` y renderizado a 60 FPS
  - [ ] 16.4 Implementar `run_continue(env, agent, model_path, config)` cargando modelo y continuando entrenamiento
  - [ ] 16.5 Implementar guardado automático del modelo al detectar `pygame.QUIT` o al finalizar entrenamiento

### Phase 8: Tests

- [ ] 17. Tests unitarios del entorno (`tests/test_environment.py`)
  - [ ] 17.1 Test: `reset()` retorna observación con shape correcto y sin NaN
  - [ ] 17.2 Test: `step(action)` retorna tupla `(obs, reward, terminated, truncated, info)` con tipos correctos
  - [ ] 17.3 Test: recompensas están en rango `[REWARD_MIN, REWARD_MAX]` para todas las acciones
  - [ ] 17.4 Test: el episodio termina cuando se recolectan todos los recursos
  - [ ] 17.5 Test: el agente no puede moverse a celdas con obstáculos

- [ ] 18. Tests unitarios del agente Q-Learning (`tests/test_q_agent.py`)
  - [ ] 18.1 Test: `select_action` con `epsilon=1.0` siempre retorna acción aleatoria en `[0, 3]`
  - [ ] 18.2 Test: `select_action` con `epsilon=0.0` siempre retorna `argmax(Q(s,·))`
  - [ ] 18.3 Test: `learn()` actualiza correctamente el Q-value con la ecuación de Bellman
  - [ ] 18.4 Test: `decay_epsilon()` nunca baja de `epsilon_min`
  - [ ] 18.5 Test: `save_model` / `load_model` produce la misma Q-table

- [ ] 19. Tests unitarios del replay buffer (`tests/test_replay_buffer.py`)
  - [ ] 19.1 Test: el buffer no excede `max_size` (descarta los más antiguos)
  - [ ] 19.2 Test: `sample(batch_size)` retorna exactamente `batch_size` transiciones
  - [ ] 19.3 Test: el buffer no es modificado por `sample()`

- [ ] 20. Tests de integración (`tests/test_training_loop.py`, `tests/test_save_load.py`)
  - [ ] 20.1 Test: ejecutar 10 episodios completos de Q-Learning en modo headless sin errores, epsilon decrece
  - [ ] 20.2 Test: ejecutar 10 episodios de DQN en modo headless sin errores (si PyTorch disponible)
  - [ ] 20.3 Test: entrenar, guardar, cargar y verificar que el agente produce las mismas acciones para los mismos estados
  - [ ] 20.4 Test: modo demo ejecuta un episodio completo sin errores con modelo cargado

- [ ] 21. Property-based tests (`tests/test_properties.py`)
  - [ ] 21.1 **[PBT]** Propiedad: para cualquier acción válida, `step()` retorna observación del mismo shape que `reset()`
  - [ ] 21.2 **[PBT]** Propiedad: `select_action()` siempre retorna entero en `[0, NUM_ACTIONS)`
  - [ ] 21.3 **[PBT]** Propiedad: la discretización del estado es determinista (misma posición → mismo estado)
  - [ ] 21.4 **[PBT]** Propiedad: el replay buffer nunca excede `max_size` tras N pushes arbitrarios

### Phase 9: Persistencia del aprendizaje y autoconciencia

- [ ] 22. Crear `utils/learning_memory.py` — persistencia del aprendizaje en MongoDB
  - [ ] 22.1 Implementar `LearningMemory` con conexión a MongoDB (colección `rl_aprendizaje`) con fallback a JSON
  - [ ] 22.2 Implementar `registrar_episodio(stats: EpisodeStats)` — guarda cada episodio con métricas
  - [ ] 22.3 Implementar `registrar_error(situacion: str, accion: int, consecuencia: str)` — registra errores frecuentes
  - [ ] 22.4 Implementar `registrar_habilidad(nombre: str, tasa_exito: float, episodios: int)` — registra habilidades aprendidas
  - [ ] 22.5 Implementar `obtener_resumen_autoconciencia() -> dict` — genera resumen legible del estado del aprendizaje
  - [ ] 22.6 Integrar `LearningMemory` en el game loop: llamar `registrar_episodio()` al final de cada episodio

- [ ] 23. Implementar análisis de errores y límites del agente
  - [ ] 23.1 Detectar situaciones de fallo recurrentes: si el agente muere >3 veces seguidas en la misma zona, registrar como "zona difícil"
  - [ ] 23.2 Calcular tasa de éxito por tipo de situación (con enemigos, sin recursos, zona explorada vs nueva)
  - [ ] 23.3 Identificar acciones que el agente evita (Q-value consistentemente bajo) como "limitaciones conocidas"
  - [ ] 23.4 Exportar `resumen_autoconciencia` al archivo `models/self_awareness.json` después de cada sesión
