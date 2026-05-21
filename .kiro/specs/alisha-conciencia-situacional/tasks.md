# Plan de Implementación: alisha-conciencia-situacional

## Overview

Implementación incremental del sistema de Conciencia Situacional de Alisha en 8 módulos Python independientes, más integración con el código existente y tests con pytest + hypothesis. Cada tarea construye sobre la anterior; el orquestador se conecta al final.

## Tasks

- [x] 1. Crear `silent_buffer.py` — búfer thread-safe de eventos
  - Implementar clase `SilentBuffer` con `collections.deque(maxlen=500)` y `threading.Lock()`
  - Método `registrar(tipo: str, datos: dict) -> None`: agrega evento con timestamp ISO 8601 automático
  - Método `vaciar() -> list[dict]`: retorna todos los eventos en orden de inserción y limpia el deque
  - Método `__len__() -> int`: retorna cantidad actual de eventos
  - Graceful degradation: ningún método lanza excepción hacia el caller
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5_

  - [ ]* 1.1 Property test — invariante de capacidad (Property 1)
    - **Property 1: Invariante de capacidad del Silent_Buffer**
    - Insertar entre 501 y 1000 eventos; verificar `len(buffer) <= 500` y que los retenidos son los más recientes
    - **Validates: Requirements 1.3, 1.4**

  - [ ]* 1.2 Property test — round-trip de `vaciar()` (Property 2)
    - **Property 2: Round-trip del método vaciar()**
    - Para N eventos insertados, `vaciar()` retorna exactamente esos N eventos en orden y deja `len == 0`
    - **Validates: Requirements 1.5**

  - [ ]* 1.3 Property test — integridad de campos del evento (Property 3)
    - **Property 3: Integridad de campos del evento registrado**
    - Para tipo y datos arbitrarios, el evento almacenado contiene `timestamp`, `tipo` y `datos`; `timestamp` es ISO 8601 válido
    - **Validates: Requirements 1.2**

- [x] 2. Crear `context_monitor.py` — recolección de contexto del entorno
  - Implementar clase `ContextMonitor` con thread daemon de baja prioridad (intervalo 30s)
  - Recolectar: app activa y título de ventana (via `win32gui`/`psutil`), hora del sistema, nivel de batería (`psutil`), cambios de ventana en el último minuto
  - Medir ritmo de escritura con hook de teclado no intrusivo (`pynput.keyboard.Listener`)
  - Método `iniciar(buffer: SilentBuffer) -> None`: arranca el thread
  - Método `detener() -> None`: detiene el thread limpiamente
  - Cada snapshot se registra en el buffer como evento tipo `contexto`
  - Graceful degradation: si `win32gui`, `psutil` o `pynput` no están disponibles, omitir el campo sin excepción
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_

  - [ ]* 2.1 Property test — resiliencia ante datos no disponibles (Property 5)
    - **Property 5: Resiliencia ante datos no disponibles**
    - Para cualquier combinación de campos `None` en el snapshot, `ContextMonitor._construir_snapshot()` no lanza excepción
    - **Validates: Requirements 2.5**

  - [ ]* 2.2 Property test — corrección del ritmo de escritura (Property 4)
    - **Property 4: Corrección del cálculo de ritmo de escritura**
    - Para lista de timestamps y duración D, `calcular_ritmo(timestamps, D)` == `len(timestamps) / D` con tolerancia ±0.01
    - **Validates: Requirements 2.2**

- [x] 3. Crear `state_vector.py` — generación y validación del State_Vector
  - Implementar función pura `generar_state_vector(eventos: list[dict]) -> dict`
  - Calcular todos los campos del modelo de datos: `apps_unicas`, `titulo_mas_frecuente`, `total_cambios_ventana`, `cambios_ventana_por_minuto`, `ritmo_escritura_promedio`, `hora_del_dia`, `bateria`, `app_dominante`, `duracion_minutos`, `actividad_detectada`
  - Si `eventos` está vacío, retornar dict con `actividad_detectada: False` y resto de campos en valores neutros
  - Implementar función pura `es_identico(sv1: dict, sv2: dict) -> bool`: compara `app_dominante`, `titulo_mas_frecuente` y `ritmo_escritura_promedio`
  - Implementar `truncar_si_necesario(sv: dict) -> dict`: recorta `apps_unicas` y `titulo_mas_frecuente` hasta que `json.dumps(sv)` sea ≤ 2048 bytes
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

  - [ ]* 3.1 Property test — completitud y tamaño del State_Vector (Property 6)
    - **Property 6: Completitud y tamaño del State_Vector**
    - Para cualquier lista no vacía de eventos, el SV generado contiene todos los campos requeridos, es serializable a JSON y tiene tamaño ≤ 2048 bytes
    - **Validates: Requirements 3.2, 3.3**

  - [ ]* 3.2 Property test — corrección de `cambios_ventana_por_minuto` (Property 7)
    - **Property 7: Corrección del campo cambios_ventana_por_minuto**
    - Para N cambios y D minutos (D > 0), `cambios_ventana_por_minuto == N / D` con tolerancia ±0.01
    - **Validates: Requirements 3.5**

- [x] 4. Checkpoint — verificar módulos base
  - Asegurar que `silent_buffer.py`, `context_monitor.py` y `state_vector.py` importan sin error
  - Ejecutar `pytest tests/test_silent_buffer.py tests/test_context_monitor.py tests/test_state_vector.py -v`
  - Asegurar que todos los tests pasan, preguntar al usuario si hay dudas antes de continuar

- [x] 5. Crear `semantic_layer.py` — traducción semántica y construcción de prompts
  - Implementar función pura `construir_prompt(sv: dict, historial_apps: Counter, registro_anterior: dict | None) -> str`
  - Aplicar traducciones semánticas por categoría de app (diseño, código, texto, navegador) según Requisito 7.2
  - Incluir siempre: instrucción de voseo rioplatense, prohibición de verbos literales, prohibición de lenguaje técnico (Requisitos 10.1, 10.2, 7.3)
  - Agregar cláusula de empatía nocturna si batería ≤ 20% AND hora entre 22:00-02:00 AND app de trabajo (Requisito 7.4)
  - Agregar cláusula de comparación temporal si `registro_anterior` no es None (Requisito 9.3)
  - Agregar cláusula de personalidad por app dominante en sesión (Requisitos 8.2, 8.3, 8.5)
  - Mantener `Counter` de frecuencia de apps en memoria de sesión (Requisito 8.4)
  - Limitar el comentario final a máximo 2 oraciones en el prompt (Requisito 10.5)
  - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 8.1, 8.2, 8.3, 8.4, 8.5, 10.1, 10.2, 10.3, 10.4, 10.5_

  - [ ]* 5.1 Property test — instrucciones obligatorias en el prompt (Property 8)
    - **Property 8: Invariante del prompt — instrucciones obligatorias**
    - Para cualquier SV con `actividad_detectada=True`, el prompt contiene voseo rioplatense, prohibición de verbos literales y prohibición de lenguaje técnico
    - **Validates: Requirements 7.3, 10.1, 10.2**

  - [ ]* 5.2 Property test — traducción semántica por categoría (Property 9)
    - **Property 9: Traducción semántica por categoría de app**
    - Para cada categoría conocida (diseño, código, texto, navegador), el prompt contiene la traducción semántica correspondiente
    - **Validates: Requirements 7.1, 7.2**

  - [ ]* 5.3 Property test — empatía nocturna (Property 10)
    - **Property 10: Prompt de empatía ante condiciones nocturnas**
    - Para SV con batería ≤ 20%, hora entre 22:00-02:00 y app de trabajo, el prompt incluye el texto de empatía
    - **Validates: Requirements 7.4**

  - [ ]* 5.4 Property test — detección de inactividad en 3 ciclos (Property 11)
    - **Property 11: Detección de inactividad en historial de 3 ciclos**
    - Para 3 SVs consecutivos con misma `app_dominante` y `total_cambios_ventana == 0`, `detectar_inactividad()` retorna `True`
    - **Validates: Requirements 5.4**

  - [ ]* 5.5 Property test — omisión por ciclos idénticos (Property 12)
    - **Property 12: Omisión de envío por ciclos idénticos**
    - Para par de SVs con `app_dominante`, `titulo_mas_frecuente` y `ritmo_escritura_promedio` idénticos, `es_identico()` retorna `True`
    - **Validates: Requirements 5.2**

  - [ ]* 5.6 Property test — personalidad por app dominante en sesión (Property 19)
    - **Property 19: Personalidad basada en app dominante en sesión**
    - Para historial donde VS Code aparece como dominante en los últimos 5 ciclos, el prompt incluye la referencia afectiva al código
    - **Validates: Requirements 8.2**

  - [ ]* 5.7 Property test — curiosidad ante app nueva (Property 20)
    - **Property 20: Curiosidad ante app nueva**
    - Para SV cuya `app_dominante` no aparece en el historial de sesión, el prompt incluye expresión de curiosidad genuina
    - **Validates: Requirements 8.5**

- [x] 6. Crear `priority_interrupt.py` — interrupciones de alta prioridad
  - Implementar clase `PriorityInterrupt` con thread daemon (intervalo 2s)
  - Monitorear título de ventana activa buscando palabras clave: "error", "fallo", "no responde", "detuvo" (case-insensitive)
  - Detectar cambios de ventana excesivos: ≥ 20 cambios en 60 segundos usando ventana deslizante de timestamps
  - Método `iniciar(buffer: SilentBuffer, callback: Callable[[str], None]) -> None`
  - Método `detener() -> None`
  - Usar `threading.Event` para señalizar al `ReflectionTimer` que reinicie su contador (Requisito 6.5)
  - Mensaje hardcoded para cambios excesivos: "Che, estás a mil, ¿no te estarás mareando con tantas pestañas?" (Requisito 6.4)
  - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5_

  - [ ]* 6.1 Property test — detección de palabras clave (Property 16)
    - **Property 16: Detección de palabras clave de alta prioridad**
    - Para cualquier string de título, `detectar_error_titulo(titulo)` retorna `True` si y solo si contiene alguna palabra clave (case-insensitive)
    - **Validates: Requirements 6.1**

  - [ ]* 6.2 Property test — detección de cambios excesivos (Property 17)
    - **Property 17: Detección de cambios de ventana excesivos**
    - Para cualquier lista de timestamps, `detectar_cambios_excesivos(timestamps)` retorna `True` si y solo si hay ≥ 20 timestamps en alguna ventana de 60s
    - **Validates: Requirements 6.3**

- [x] 7. Crear `atlas_memory.py` — memoria de largo plazo comparativa
  - Implementar clase `AtlasMemory` que lee/escribe la clave `atlas_situacional` en `ia_recuerdos.json`
  - Método `guardar_ciclo(sv: dict) -> None`: agrega registro con `timestamp`, `hora_franja`, `apps_unicas`, `app_dominante`, `ritmo_escritura_promedio`, `resumen_semantico`
  - Método `buscar_franja_horaria(hora: datetime) -> dict | None`: busca registro del día anterior en franja ±30 minutos
  - Método `limpiar_antiguos() -> None`: elimina registros con timestamp > 7 días
  - Graceful degradation: si `ia_recuerdos.json` está corrupto o no existe, inicializar con lista vacía
  - No modificar las claves `recuerdos` ni `temas` del archivo existente
  - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6_

  - [ ]* 7.1 Property test — invariante de retención de 7 días (Property 13)
    - **Property 13: Invariante de retención de 7 días en Atlas_Memory**
    - Para secuencia de registros con fechas variadas, después de `limpiar_antiguos()` solo permanecen los de los últimos 7 días
    - **Validates: Requirements 9.5, 9.6**

  - [ ]* 7.2 Property test — round-trip de persistencia (Property 14)
    - **Property 14: Round-trip de persistencia en Atlas_Memory**
    - Para cualquier SV guardado, el registro leído contiene `timestamp`, `hora_franja`, `apps_unicas`, `app_dominante` y `resumen_semantico` consistentes
    - **Validates: Requirements 9.1**

  - [ ]* 7.3 Property test — prompt de comparación temporal (Property 15)
    - **Property 15: Prompt de comparación temporal con registro anterior**
    - Para par (registro_anterior, SV_actual) con datos válidos, el prompt incluye resumen del día anterior y resumen actual
    - **Validates: Requirements 9.3**

- [x] 8. Crear `reflection_timer.py` — temporizador de reflexión y voz situacional
  - Implementar clase `ReflectionTimer` con thread daemon (intervalo 10 minutos)
  - Método `iniciar(buffer: SilentBuffer, atlas: AtlasMemory, callback: Callable[[str], None]) -> None`
  - Método `detener() -> None`
  - Método `reiniciar_contador() -> None`: usado por `PriorityInterrupt` vía `threading.Event`
  - En cada ciclo: vaciar buffer → generar SV → comparar con historial → si no es idéntico y hay actividad → construir prompt vía `SemanticLayer` → llamar LLM con timeout 15s → invocar callback con respuesta
  - Mantener `deque(maxlen=3)` de SVs anteriores para detección de inactividad (Requisito 5.3)
  - Si LLM no responde en 15s, omitir ciclo silenciosamente (Requisito 4.6)
  - Vaciar buffer igualmente cuando se omite por inactividad (Requisito 5.5)
  - Llamar `atlas.guardar_ciclo()` y `atlas.limpiar_antiguos()` al final de cada ciclo exitoso
  - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 5.1, 5.2, 5.3, 5.4, 5.5_

  - [ ]* 8.1 Unit test — invariante del historial de 3 SVs (Property 18)
    - **Property 18: Invariante del historial de State_Vectors**
    - Para N > 3 ciclos de reflexión, el historial mantiene exactamente 3 elementos (los más recientes)
    - **Validates: Requirements 5.3**

  - [ ]* 8.2 Unit test — omisión por timeout del LLM
    - Mockear LLM para que tarde > 15s; verificar que el ciclo se omite sin excepción y el buffer queda vacío
    - _Requirements: 4.6_

  - [ ]* 8.3 Unit test — reinicio de contador por Priority_Interrupt
    - Verificar que `reiniciar_contador()` resetea el timer y el próximo ciclo ocurre 10 minutos después
    - _Requirements: 6.5_

- [x] 9. Checkpoint — verificar módulos de procesamiento
  - Ejecutar `pytest tests/ -v --tb=short`
  - Asegurar que todos los tests pasan, preguntar al usuario si hay dudas antes de continuar

- [x] 10. Crear `situational_awareness.py` — orquestador principal
  - Implementar clase `SituationalAwareness` que instancia y conecta todos los módulos
  - Método `iniciar(callback: Callable[[str], None]) -> None`: crea instancias de `SilentBuffer`, `ContextMonitor`, `PriorityInterrupt`, `AtlasMemory`, `ReflectionTimer` y los arranca en orden
  - Método `detener() -> None`: detiene todos los módulos en orden inverso
  - Pasar el mismo `callback` a `PriorityInterrupt` y `ReflectionTimer`
  - Pasar el `threading.Event` de reinicio desde `PriorityInterrupt` a `ReflectionTimer`
  - Graceful degradation: si algún módulo falla al iniciar, loguear silenciosamente y continuar con los demás
  - _Requirements: todos los módulos integrados_

  - [ ]* 10.1 Unit test — integración de arranque completo
    - Verificar que `SituationalAwareness.iniciar()` arranca todos los threads sin excepción
    - Verificar que `detener()` los detiene limpiamente
    - _Requirements: 4.5, 2.4_

- [x] 11. Integrar con el código existente de Alisha
  - En `autonomous_agent.py`, agregar import de `SituationalAwareness` al final del archivo (no modificar lógica existente)
  - En la función `iniciar_agente()`, después de `_agent.iniciar()`, instanciar y arrancar `SituationalAwareness` pasando el mismo `callback_interrupcion`
  - Agregar referencia al objeto `SituationalAwareness` en el singleton `_agent` para poder detenerlo con `detener()`
  - Verificar que el hilo principal de PyQt6 no se bloquea con ningún import nuevo
  - _Requirements: integración no destructiva con código existente_

  - [ ]* 11.1 Unit test — no regresión en autonomous_agent
    - Verificar que `iniciar_agente()` sigue funcionando con y sin `SituationalAwareness` disponible
    - Mockear `SituationalAwareness` para aislar el test del sistema completo
    - _Requirements: 2.4_

- [ ] 12. Crear suite de tests `tests/` con pytest + hypothesis
  - Crear `tests/__init__.py` vacío
  - Crear `tests/conftest.py` con fixtures compartidos: `buffer_vacio`, `sv_ejemplo`, `eventos_ejemplo`
  - Crear archivos de test por módulo: `test_silent_buffer.py`, `test_context_monitor.py`, `test_state_vector.py`, `test_semantic_layer.py`, `test_atlas_memory.py`, `test_priority_interrupt.py`, `test_reflection_timer.py`
  - Configurar `hypothesis` con `@settings(max_examples=100)` en todos los property tests
  - Mockear LLM (Ollama) en todos los tests con `unittest.mock.patch`
  - Mockear `ia_recuerdos.json` usando `tmp_path` de pytest para no tocar el archivo real
  - _Requirements: todos_

- [x] 13. Checkpoint final — suite completa
  - Ejecutar `pytest tests/ -v --tb=short --hypothesis-seed=0`
  - Asegurar que todos los tests pasan, preguntar al usuario si hay dudas antes de continuar

## Notes

- Las tareas marcadas con `*` son opcionales y pueden saltarse para un MVP más rápido
- Cada tarea referencia requisitos específicos para trazabilidad
- Los property tests usan `hypothesis` con `@settings(max_examples=100)`
- El LLM (Ollama) se mockea en todos los tests; no se hacen llamadas reales
- `ia_recuerdos.json` se mockea con `tmp_path` de pytest para no corromper datos reales
- Todos los threads son `daemon=True` — se cierran solos cuando el proceso principal termina
- Ningún módulo nuevo modifica archivos existentes; solo `autonomous_agent.py` recibe un import adicional al final
