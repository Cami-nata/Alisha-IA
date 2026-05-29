# Plan de Implementación: Alisha Agente Operativo

## Visión General

Implementar el Agente Operativo Real de Alisha en Python 3.11+ sobre Windows 11, siguiendo el principio **fail-silent**: cada componente nuevo está aislado con manejo de excepciones exhaustivo. El orden de implementación respeta las dependencias entre módulos: primero los módulos sin dependencias externas nuevas, luego los que dependen de ellos, y finalmente las integraciones mínimas en archivos existentes.

## Tareas

- [x] 1. Implementar `memory_db.py` — Persistencia SQLite con fallback a JSON
  - [x] 1.1 Crear `memory_db.py` con la clase `MemoryDB` e inicialización de base de datos
    - Crear el archivo `alisha_memory.db` en el directorio raíz con `sqlite3`
    - Implementar `__init__(self, db_path: str = "alisha_memory.db")` con creación de tablas y modo WAL
    - Crear las tablas: `conversaciones`, `conversaciones_archivo`, `preferencias`, `sesiones` con los índices definidos en el diseño
    - Implementar `_fallback_to_json(self)` que carga `ia_recuerdos.json` y `memory.json` si SQLite falla
    - _Requisitos: 9.1, 9.2, 9.7_

  - [x] 1.2 Implementar operaciones CRUD de conversaciones y preferencias
    - Implementar `save_conversation(self, entrada: str, respuesta: str, estado_emocional: str) -> None` con timeout de 5s
    - Implementar `load_recent(self, n: int = 20) -> list[dict]` que carga desde SQLite o fallback JSON
    - Implementar `buscar_contexto(self, query: str) -> list[dict]` con LIKE en campos `entrada` y `respuesta`, retorna máximo 5 resultados
    - Implementar `save_preference(self, clave: str, valor: str) -> None` y `get_preference(self, clave: str) -> Optional[str]`
    - _Requisitos: 9.3, 9.4, 9.5, 9.8_

  - [x] 1.3 Implementar gestión de sesiones y archivado automático
    - Implementar `start_session(self) -> int` que inserta en tabla `sesiones` y retorna el `session_id`
    - Implementar `end_session(self, session_id: int, resumen: str) -> None` que actualiza `fin` y `resumen`
    - Implementar `_archive_old_records(self) -> None` que mueve registros a `conversaciones_archivo` cuando `conversaciones` supera 10.000 filas
    - Llamar `_archive_old_records()` automáticamente al final de `save_conversation`
    - _Requisitos: 9.2, 9.6_

  - [ ]* 1.4 Escribir test de propiedad: round-trip de conversación
    - **Propiedad 5: MemoryDB — round-trip de conversación**
    - **Valida: Requisito 9.3**
    - Usar `@given(st.text(min_size=1), st.text(min_size=1), st.text(min_size=1))` con base de datos en memoria (`:memory:`)
    - Verificar que `save_conversation` + `load_recent` retorna los mismos valores de entrada, respuesta y estado emocional

  - [ ]* 1.5 Escribir test de propiedad: búsqueda retorna subconjunto relevante
    - **Propiedad 6: MemoryDB — búsqueda retorna subconjunto relevante**
    - **Valida: Requisito 9.5**
    - Usar `@given(st.lists(...), st.text(min_size=1))` para poblar la DB y luego buscar
    - Verificar que todos los resultados de `buscar_contexto(query)` contienen la query en `entrada` o `respuesta`

  - [ ]* 1.6 Escribir tests de ejemplo para `MemoryDB`
    - Test: inicialización crea las 4 tablas correctamente
    - Test: fallback a JSON cuando se pasa una ruta de DB inválida
    - Test: `_archive_old_records` mueve registros cuando hay más de 10.000 filas
    - Test: `get_preference` retorna `None` para clave inexistente
    - _Requisitos: 9.1, 9.7_

- [ ] 2. Checkpoint — Verificar `memory_db.py`
  - Asegurar que todos los tests pasan. Consultar al usuario si surgen dudas sobre el esquema de datos.

- [x] 3. Implementar `natural_mouse.py` — Movimientos curvos con Bézier
  - [x] 3.1 Crear `natural_mouse.py` con la clase `NaturalMouse` y funciones matemáticas
    - Implementar `_bezier_curve(self, p0, p1, p2, steps) -> list[tuple]` que genera puntos de la curva cuadrática
    - Implementar `_ease_in_out(self, t: float) -> float` para la función de aceleración/desaceleración
    - Implementar `_calcular_duracion(self, distancia: float) -> float` que retorna valor en rango [0.15, 1.2] segundos
    - El punto de control aleatorio debe desplazarse entre 20 y 80 píxeles del eje directo
    - _Requisitos: 3.1, 3.2, 3.3_

  - [x] 3.2 Implementar `mover_a` y `click_natural` con manejo de errores
    - Implementar `mover_a(self, x: int, y: int) -> None`: si distancia < 50px usar movimiento lineal directo; si no, usar Bézier con micro-variaciones ±2px en cada paso
    - Implementar `click_natural(self, x: int, y: int) -> None` que llama `mover_a` y luego `pyautogui.click`
    - Capturar `pyautogui.FailSafeException` en ambas funciones: detener movimiento y registrar sin propagar
    - _Requisitos: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6_

  - [x]* 3.3 Escribir test de propiedad: la curva de Bézier siempre termina en el destino
    - **Propiedad 3: NaturalMouse — la curva de Bézier siempre termina en el destino**
    - **Valida: Requisito 3.1**
    - Usar `@given(st.integers(0, 1920), st.integers(0, 1080), st.integers(0, 1920), st.integers(0, 1080))` para origen y destino
    - Verificar que el último punto de `_bezier_curve` está dentro de ±1 píxel del destino

  - [x]* 3.4 Escribir test de propiedad: duración acotada y proporcional a la distancia
    - **Propiedad 4: NaturalMouse — duración acotada y proporcional a la distancia**
    - **Valida: Requisito 3.2, 3.3**
    - Usar `@given(st.floats(0.0, 3000.0))` para distancias arbitrarias
    - Verificar que `_calcular_duracion` retorna valor en [0.15, 1.2] y que es monótonamente no-decreciente para distancias > 50px

  - [x]* 3.5 Escribir tests de ejemplo para `NaturalMouse`
    - Test: distancia < 50px usa movimiento lineal (sin punto de control Bézier)
    - Test: `FailSafeException` es capturada y no se propaga
    - Test: micro-variaciones están dentro de ±2px
    - _Requisitos: 3.3, 3.4, 3.5_

- [x] 4. Implementar `mouse_coordinator.py` — Detección de movimiento del usuario
  - [x] 4.1 Crear `mouse_coordinator.py` con la clase `MouseCoordinator`
    - Implementar `__init__` con referencia al `EventBus` y configuración del umbral de 5px
    - Implementar `_poll_loop(self) -> None` que corre en hilo daemon con polling cada 100ms
    - Intentar importar `pynput`; si no está disponible, usar `pyautogui.position()` como fallback sin interrumpir
    - _Requisitos: 5.1, 5.6_

  - [x] 4.2 Implementar detección de movimiento y publicación de eventos
    - Implementar `start(self) -> None` y `stop(self) -> None` para el hilo de polling
    - Implementar `is_user_active(self) -> bool` que retorna `True` si el usuario movió el mouse en los últimos 3 segundos
    - WHEN la distancia euclidiana entre posición anterior y actual supera 5px: publicar evento `user_mouse_active` en EventBus y actualizar `chibi_state.json` con `"ultimo_movimiento_usuario"` (timestamp actual)
    - _Requisitos: 5.1, 5.2, 5.3, 5.5_

  - [ ]* 4.3 Escribir test de propiedad: umbral de detección de movimiento
    - **Propiedad 12: MouseCoordinator — umbral de detección de movimiento**
    - **Valida: Requisito 5.2**
    - Usar `@given(st.tuples(st.floats(0, 1920), st.floats(0, 1080)), st.tuples(st.floats(0, 1920), st.floats(0, 1080)))` para pares de posiciones
    - Verificar que el evento se publica si y solo si la distancia euclidiana > 5px (mockear EventBus)

  - [ ]* 4.4 Escribir tests de ejemplo para `MouseCoordinator`
    - Test: fallback a `pyautogui.position()` cuando `pynput` no está disponible
    - Test: `is_user_active()` retorna `False` después de 3 segundos sin movimiento
    - Test: `chibi_state.json` se actualiza con `"ultimo_movimiento_usuario"` al detectar movimiento
    - _Requisitos: 5.5, 5.6_

- [x] 5. Implementar `gemini_vision.py` — Análisis semántico de capturas
  - [x] 5.1 Crear `gemini_vision.py` con la clase `GeminiVision` y buffer circular
    - Implementar `__init__` con buffer circular de capacidad 5 (lista de dicts `{description, timestamp}`)
    - Implementar `_analyze(self, img_bytes: bytes) -> Optional[str]` que envía la imagen a Gemini con el prompt especificado y timeout de 15s
    - Capturar toda excepción de la API: registrar error, esperar 60s y reintentar; nunca propagar
    - _Requisitos: 6.2, 6.6, 6.7_

  - [x] 5.2 Implementar captura periódica con control de CPU
    - Implementar `_capture_loop(self) -> None` con intervalo aleatorio entre 10 y 15 segundos
    - Antes de cada captura, verificar uso de CPU con `psutil.cpu_percent()`; si > 70%, pausar hasta que baje del 60%
    - Implementar `capture_and_analyze(self) -> Optional[str]` para captura inmediata bajo demanda
    - Implementar `start(self) -> None` y `stop(self) -> None` para el hilo daemon
    - _Requisitos: 6.1, 6.5_

  - [x] 5.3 Implementar `get_latest_description` con filtro de frescura
    - Implementar `get_latest_description(self) -> Optional[str]` que retorna la descripción más reciente solo si tiene menos de 30 segundos de antigüedad; retorna `None` si el buffer está vacío o la descripción es antigua
    - _Requisitos: 6.3, 6.4_

  - [ ]* 5.4 Escribir test de propiedad: buffer circular retiene las últimas 5 descripciones
    - **Propiedad 10: GeminiVision — buffer circular retiene las últimas 5 descripciones**
    - **Valida: Requisito 6.3**
    - Usar `@given(st.lists(st.text(min_size=1), min_size=1, max_size=20))` para secuencias de descripciones
    - Verificar que el buffer contiene exactamente `min(N, 5)` descripciones y que son las N más recientes

  - [ ]* 5.5 Escribir test de propiedad: filtro de frescura de 30 segundos
    - **Propiedad 11: GeminiVision — filtro de frescura de 30 segundos**
    - **Valida: Requisito 6.4**
    - Usar `@given(st.floats(0.0, 120.0))` para antigüedad en segundos
    - Verificar que `get_latest_description` retorna la descripción si antigüedad < 30s y `None` si antigüedad >= 30s (mockear `time.time`)

  - [ ]* 5.6 Escribir tests de ejemplo para `GeminiVision`
    - Test: pausa cuando CPU > 70% (mockear `psutil.cpu_percent`)
    - Test: error de API no se propaga y se reintenta después de 60s
    - Test: buffer vacío retorna `None` en `get_latest_description`
    - _Requisitos: 6.5, 6.6, 6.7_

- [ ] 6. Checkpoint — Verificar módulos independientes
  - Asegurar que todos los tests de `memory_db.py`, `natural_mouse.py`, `mouse_coordinator.py` y `gemini_vision.py` pasan. Consultar al usuario si surgen dudas.

- [x] 7. Implementar `agent_loop.py` — EventBus, ScreenWatcher, StateMapper y AgentLoop
  - [x] 7.1 Implementar `EventBus` thread-safe
    - Crear `EventBus` con `subscribe(self, event_type: str, handler: Callable) -> None` y `publish(self, event_type: str, data: dict) -> None`
    - Usar `threading.Lock` para proteger el diccionario de suscriptores
    - `publish` debe invocar cada handler en el hilo del publicador; capturar excepciones de handlers individuales sin detener la entrega a los demás
    - Eventos soportados: `window_changed`, `file_changed`, `media_changed`, `app_context_changed`, `user_mouse_active`
    - _Requisitos: 1.2, 1.3, 1.4_

  - [ ]* 7.2 Escribir test de propiedad: EventBus entrega a todos los suscriptores exactamente una vez
    - **Propiedad 8: EventBus — entrega a todos los suscriptores exactamente una vez**
    - **Valida: Requisito 1.2, 1.3, 1.4**
    - Usar `@given(st.integers(1, 10), st.dictionaries(st.text(), st.text()))` para N handlers y datos de evento
    - Verificar que publicar un evento invoca exactamente N handlers, cada uno exactamente una vez, con los datos sin modificar

  - [x] 7.3 Implementar `ScreenWatcher` con detección de ventana, archivos y medios
    - Implementar `_detect_window(self) -> None` usando `ctypes.windll.user32` para obtener título y proceso de la ventana en primer plano; publicar `window_changed` si cambió
    - Implementar `_detect_files(self) -> None` usando `os.stat` en el directorio de trabajo; publicar `file_changed` si un archivo fue creado/modificado en los últimos 30s
    - Implementar `_detect_media(self) -> None` llamando `alisha_media.get_media_info()`; publicar `media_changed` si título o artista cambió
    - Implementar `_categorize_app(self, title: str, process: str) -> str` que retorna el rol según la categoría de la app
    - Implementar `start(self) -> None` y `stop(self) -> None` para el hilo daemon con ciclos de 5 segundos
    - _Requisitos: 1.2, 1.3, 1.4, 4.1, 4.2, 4.3, 4.4, 4.5, 4.7, 7.1, 7.2_

  - [ ]* 7.4 Escribir test de propiedad: clasificación de apps asigna rol correcto
    - **Propiedad 9: ScreenWatcher — clasificación de apps asigna rol correcto**
    - **Valida: Requisito 4.2, 4.3, 4.4, 4.5, 4.7**
    - Usar `@given(st.sampled_from([...]))` con títulos de apps conocidas y desconocidas
    - Verificar que `_categorize_app` retorna el rol correcto para cada categoría y `"companion"` para apps desconocidas

  - [x] 7.5 Implementar `StateMapper` con escritura en `chibi_state.json`
    - Implementar `apply(self, state: str) -> None` que traduce {IDLE, THINKING, WORKING, OVERLOADED} a parámetros Live2D y escribe en `chibi_state.json` preservando todos los campos existentes
    - Implementar `transition_to_idle(self) -> None` con transición gradual de 2 segundos antes de escribir el estado IDLE
    - IF `chibi_state.json` no existe o está corrupto: crear archivo nuevo con valores por defecto sin lanzar excepción
    - Usar `threading.Lock` para escrituras concurrentes al archivo JSON
    - _Requisitos: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7_

  - [ ]* 7.6 Escribir test de propiedad: StateMapper preserva campos existentes
    - **Propiedad 1: StateMapper preserva campos existentes**
    - **Valida: Requisito 2.5**
    - Usar `@given(st.dictionaries(st.text(), st.one_of(st.text(), st.floats(), st.booleans())))` para campos preexistentes
    - Verificar que después de `apply(state)`, todos los campos preexistentes siguen presentes con sus valores originales

  - [ ]* 7.7 Escribir test de propiedad: StateMapper mapea estados a rangos correctos
    - **Propiedad 2: StateMapper mapea estados a rangos de parámetros correctos**
    - **Valida: Requisito 2.1, 2.2, 2.3, 2.4**
    - Usar `@given(st.sampled_from(["IDLE", "THINKING", "WORKING", "OVERLOADED"]))` para estados válidos
    - Verificar que los parámetros Live2D resultantes satisfacen las restricciones de rango de cada estado

  - [x] 7.8 Implementar `AgentLoop` — bucle central de percepción-decisión-acción
    - Implementar `__init__` que instancia `EventBus`, `ScreenWatcher`, `MouseCoordinator`, `GeminiVision` y `MemoryDB` como sub-componentes; suscribir handlers para cada tipo de evento
    - Implementar `_cycle(self) -> None` con ciclo de 5 segundos: percibir → decidir → actuar; capturar toda excepción y continuar el siguiente ciclo
    - Implementar `_handle_event(self, event_type: str, data: dict) -> None` que despacha eventos a los handlers correspondientes
    - Handler `app_context_changed`: actualizar `"rol_activo"` en `chibi_state.json`
    - Handler `user_mouse_active`: cancelar operaciones de `NaturalMouse` en curso y cambiar estado a IDLE; esperar 3s sin movimiento antes de permitir nuevas operaciones de mouse
    - Handler `media_changed`: actualizar `"media_actual"` en `chibi_state.json`; activar gesto de tarareo o ojo_en_blanco según afinidad en `alisha_identity.py`
    - Implementar `start(self) -> None` y `stop(self) -> None` para el hilo daemon
    - Implementar `get_status(self) -> dict` que retorna el estado de todos los sub-componentes
    - Escribir heartbeat en `chibi_state.json` bajo `"agent_heartbeat"` cada 30 segundos
    - _Requisitos: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 4.6, 5.3, 5.4, 7.2, 7.4, 7.7_

  - [ ]* 7.9 Escribir tests de ejemplo para `agent_loop.py`
    - Test: `AgentLoop` inicia todos los sub-componentes sin errores
    - Test: excepción en `_cycle` es capturada y el bucle continúa
    - Test: heartbeat se escribe en `chibi_state.json` cada 30s (mockear tiempo)
    - Test: `get_status()` retorna dict con todos los sub-componentes
    - Test: handler `user_mouse_active` cancela operaciones de mouse y espera 3s
    - _Requisitos: 1.1, 1.5, 1.6, 5.3, 5.4, 10.7_

- [ ] 8. Checkpoint — Verificar `agent_loop.py`
  - Asegurar que todos los tests pasan. Verificar que el EventBus, ScreenWatcher, StateMapper y AgentLoop funcionan correctamente en conjunto.

- [x] 9. Implementar `assistance_protocol.py` — Protocolo de asistencia de 4 pasos
  - [x] 9.1 Crear `assistance_protocol.py` con la clase `AssistanceProtocol` y detección de palabras clave
    - Implementar `__init__` con referencia a `GeminiVision`, `MemoryDB` y `StateMapper`
    - Definir `TRIGGER_KEYWORDS = {"ayudame con", "hacé un", "creá un", "analizá", "buscá info sobre"}`
    - Implementar `should_trigger(self, message: str) -> bool` con comparación case-insensitive
    - _Requisitos: 8.1_

  - [ ]* 9.2 Escribir test de propiedad: detección de palabras clave es exhaustiva y precisa
    - **Propiedad 7: AssistanceProtocol — detección de palabras clave es exhaustiva y precisa**
    - **Valida: Requisito 8.1**
    - Usar `@given(st.text())` para mensajes arbitrarios
    - Verificar que `should_trigger` retorna `True` si y solo si el mensaje contiene al menos una keyword (case-insensitive)

  - [x] 9.3 Implementar los 4 pasos del protocolo de asistencia
    - Implementar `_step1_capture(self) -> Optional[str]`: llamar `GeminiVision.capture_and_analyze()` para obtener contexto visual
    - Implementar `_step2_generate(self, context: str, request: str) -> str`: consultar `brain.py` con contexto visual y solicitud del usuario
    - Implementar `_step3_propose(self, proposal: str, socketio) -> None`: emitir evento SocketIO `"propuesta_asistencia"` con el JSON definido en el diseño
    - Implementar `_step4_create(self, proposal: str) -> str`: crear archivo usando funciones de `actions.py`; retornar ruta del archivo creado
    - _Requisitos: 8.2, 8.3, 8.4, 8.5, 8.6_

  - [x] 9.4 Implementar `execute` con manejo de errores y notificaciones en voseo
    - Implementar `execute(self, message: str, socketio) -> None` que corre en hilo separado y ejecuta los 4 pasos en secuencia
    - Implementar `_notify_error(self, step: int, error: str, socketio) -> None` que emite mensaje en voseo rioplatense explicando el problema y ofreciendo continuar sin ese paso
    - IF cualquier paso falla: llamar `_notify_error` y continuar con el siguiente paso si es posible
    - Actualizar estado operativo a WORKING al iniciar y a IDLE al completar o fallar (usando `StateMapper`)
    - Emitir evento SocketIO `"propuesta_confirmada"` con la ruta del archivo al completar el Paso 4
    - _Requisitos: 8.7, 8.8_

  - [ ]* 9.5 Escribir tests de ejemplo para `AssistanceProtocol`
    - Test: `execute` con mock de `brain.py` y `socketio` completa los 4 pasos
    - Test: fallo en Paso 1 notifica al usuario y continúa con Paso 2
    - Test: estado cambia a WORKING al iniciar y a IDLE al completar
    - Test: evento `"propuesta_confirmada"` se emite con la ruta del archivo
    - _Requisitos: 8.2, 8.3, 8.4, 8.5, 8.6, 8.7, 8.8_

- [ ] 10. Checkpoint — Verificar `assistance_protocol.py`
  - Asegurar que todos los tests pasan. Consultar al usuario si surgen dudas sobre el flujo de confirmación del usuario.

- [x] 11. Integraciones mínimas en archivos existentes
  - [x] 11.1 Modificar `actions.py` — Reemplazar llamadas directas a PyAutoGUI con `NaturalMouse`
    - Importar `NaturalMouse` desde `natural_mouse.py` al inicio del archivo
    - Crear una instancia singleton de `NaturalMouse` a nivel de módulo
    - Reemplazar todas las llamadas a `pyautogui.moveTo(x, y)` con `natural_mouse.mover_a(x, y)`
    - Reemplazar todas las llamadas a `pyautogui.click(x, y)` con `natural_mouse.click_natural(x, y)`
    - _Requisitos: 3.6_

  - [x] 11.2 Modificar `web_app.py` — Agregar endpoint de status y evento SocketIO
    - Agregar endpoint `GET /api/agent/status` que llama `agent_loop.get_status()` y retorna JSON; si `AgentLoop` no está disponible, retornar `{"error": "AgentLoop no iniciado"}`
    - Registrar el evento SocketIO `"propuesta_asistencia"` para que el frontend pueda recibirlo (no requiere handler del lado servidor, solo documentar que se emite desde `AssistanceProtocol`)
    - _Requisitos: 10.6_

  - [x] 11.3 Modificar `Alisha_IA.py` — Iniciar `AgentLoop` como hilo daemon
    - Importar `AgentLoop` desde `agent_loop.py`
    - Después de iniciar el servidor web y antes de iniciar el ícono de bandeja, agregar las 4 líneas de inicio del `AgentLoop`:
      ```python
      try:
          agent_loop = AgentLoop()
          agent_loop.start()
      except Exception as e:
          print(f"[Alisha_IA] AgentLoop no pudo iniciar: {e}")
      ```
    - En el handler de cierre de bandeja, llamar `agent_loop.stop()` antes de terminar el proceso
    - Mantener el orden de inicio existente: servidor web → Live2D → saludo inicial → AgentLoop → bandeja
    - _Requisitos: 10.1, 10.2, 10.3, 10.4, 10.5_

  - [ ]* 11.4 Escribir tests de ejemplo para las integraciones
    - Test: `Alisha_IA.py` continúa iniciando si `AgentLoop` lanza excepción al iniciar
    - Test: `/api/agent/status` retorna JSON válido con todos los sub-componentes
    - Test: `actions.py` usa `NaturalMouse` en lugar de `pyautogui` directamente
    - _Requisitos: 10.1, 10.4, 10.6_

- [ ] 12. Checkpoint final — Verificar integración completa
  - Asegurar que todos los tests pasan (unitarios, de propiedades y de integración).
  - Verificar que `Alisha_IA.py` inicia sin errores con el `AgentLoop` activo.
  - Verificar que el endpoint `/api/agent/status` responde correctamente.
  - Consultar al usuario si surgen dudas antes de cerrar la implementación.

## Notas

- Las tareas marcadas con `*` son opcionales y pueden omitirse para un MVP más rápido
- Cada tarea referencia requisitos específicos para trazabilidad
- Los checkpoints aseguran validación incremental antes de avanzar
- Los tests de propiedades usan `hypothesis` (ya presente en el proyecto, ver `.hypothesis/`)
- Los tests de ejemplo usan `pytest`
- El principio **fail-silent** debe aplicarse en toda la implementación: toda excepción se captura y registra, nunca se propaga al sistema principal
- Los archivos `brain.py`, `cabina_virtual.py` y `tts_engine.py` **no deben modificarse**
- `agent_memory.py` debe seguir funcionando sin cambios (compatibilidad garantizada por `MemoryDB`)
