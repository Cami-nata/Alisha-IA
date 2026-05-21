# Implementation Plan: alisha-mejoras-core

## Overview

Plan de implementación incremental para las 10 mejoras de Alisha IA. Las tareas están organizadas por módulo afectado, construyendo desde las funciones puras y testeables hacia la integración final. Cada tarea referencia los requisitos específicos que satisface.

## Tasks

- [x] 1. Implementar `smooth_damp` y `EstadoInterno` en `cabina_virtual.py`
  - [x] 1.1 Agregar la función de módulo `smooth_damp(current, target, vel, smooth_time, dt, max_speed=8.0)` en `cabina_virtual.py`
    - Implementar el algoritmo de resorte amortiguado estilo Unity con `omega = 2.0 / smooth_time`, `x = omega * dt`, `exp_factor = 1.0 / (1.0 + x + 0.48*x² + 0.235*x³)`
    - Aplicar clamp de velocidad máxima con `max_speed * dt`
    - La función debe ser de módulo (no método de clase) para facilitar el testing
    - _Requirements: 1.1, 1.2_

  - [x]* 1.2 Escribir property test P1 — SmoothDamp converge sin overshoot
    - **Property 1: SmoothDamp converge sin overshoot**
    - **Validates: Requirements 1.1, 1.2**
    - Crear `tests/test_avatar_engine.py` con `test_smooth_damp_converges_no_overshoot` usando Hypothesis
    - Verificar convergencia en 120 frames y ausencia de overshoot cuando `current < target`

  - [x] 1.3 Agregar métodos `amplitud_balanceo()` y `velocidad_balanceo()` a la clase `EstadoInterno`
    - `amplitud_balanceo()`: fórmula `1.5 + flow * 2.0 + dopamina * 0.8` con clamp a [1.5, 5.0]
    - `velocidad_balanceo()`: fórmula `0.20 + flow * 0.25` con clamp a [0.20, 0.45]
    - Agregar campos `flow: float = 0.0` y `dopamina: float = 0.7` si no existen
    - _Requirements: 2.1, 2.2, 2.4_

  - [x]* 1.4 Escribir property test P3 — Amplitud y velocidad de balanceo en rango válido
    - **Property 3: Amplitud y velocidad de balanceo siempre en rango válido**
    - **Validates: Requirements 2.1, 2.2, 2.4**
    - Agregar `test_amplitud_velocidad_balanceo_range` en `tests/test_avatar_engine.py`
    - Cubrir todo el espacio `flow ∈ [0.0, 1.0]` × `dopamina ∈ [0.0, 1.0]` con 200 ejemplos

- [x] 2. Implementar micro-variaciones orgánicas y corrección OpenGL en `cabina_virtual.py`
  - [x] 2.1 Agregar la clase `MicroVariaciones` con fases aleatorias por sesión
    - Constantes: `FREQ_BREATH = 0.18`, `FREQ_GAZE_A = 0.07`, `FREQ_GAZE_B = 0.13`
    - Generar `_phase_breath`, `_phase_gaze_a`, `_phase_gaze_b` con `random.uniform(0, 2π)` en `__init__`
    - Implementar métodos `breath(t)` y `gaze_x(t)` según el diseño
    - Aplicar micro-variaciones solo cuando `hablando == False` y han pasado ≥ 2.0s desde la última interacción; congelar en último valor calculado en caso contrario
    - _Requirements: 1.3, 1.4, 1.5_

  - [x] 2.2 Agregar la función `es_pixel_transparente(r, g, b)` en `cabina_virtual.py`
    - Condición: `r < 30 AND g ∈ [225, 255] AND b < 30`
    - Función de módulo (no método) para facilitar el testing
    - _Requirements: 3.4_

  - [x]* 2.3 Escribir property test P6 — Clasificación de píxel transparente correcta
    - **Property 6: Clasificación de píxel transparente es correcta para todo (r, g, b)**
    - **Validates: Requirements 3.4**
    - Agregar `test_pixel_transparente_clasificacion` en `tests/test_avatar_engine.py`
    - Usar 500 ejemplos con `r, g, b ∈ [0, 255]`; verificar que el resultado coincide exactamente con la condición booleana

  - [x] 2.4 Integrar `smooth_damp`, `MicroVariaciones` y `es_pixel_transparente` en el loop de renderizado de `cabina_virtual.py`
    - Reemplazar asignaciones directas de parámetros Live2D por llamadas a `smooth_damp` con `smooth_time=0.12`
    - Aplicar `MicroVariaciones` a `ParamBreath`, `ParamEyeBallX`, `ParamEyeBallY` en estado idle
    - Usar `es_pixel_transparente` para activar/desactivar click-through; mantener estado anterior si `glReadPixels` lanza excepción
    - Aplicar clamp a todos los parámetros antes de `SetParameterValue`; capturar excepciones de `live2d.v3` con log `[Avatar]`
    - _Requirements: 1.1, 1.2, 1.3, 1.6, 1.7, 3.4, 3.5_

  - [x] 2.5 Configurar color key OpenGL en la inicialización de la ventana GLFW
    - Llamar a `SetLayeredWindowAttributes` con `R=0, G=255, B=0` (`COLORREF 0x0000FF00`) y flag `LWA_COLORKEY`
    - Si retorna 0, loggear `[Avatar] Error color key:` y abortar inicialización
    - Limpiar framebuffer con `(0.0, 1.0, 0.0, 1.0)` antes de cada frame
    - _Requirements: 3.1, 3.2, 3.3_

- [-] 3. Checkpoint — Verificar módulo `cabina_virtual.py`
  - Asegurar que todos los tests de `tests/test_avatar_engine.py` pasen. Consultar al usuario si hay dudas.

- [x] 4. Implementar Lip-Sync en `tts_engine.py`
  - [x] 4.1 Agregar la función `calcular_amplitudes_rms(audio_bytes, sample_rate=24000)` en `tts_engine.py`
    - Usar `numpy` y `pydub` para calcular RMS por chunks de 40ms (chunk_size = `sample_rate * 0.040`)
    - Normalizar con `amp = min(1.0, rms / 8000.0)`
    - Fallback sinusoidal si `numpy`/`pydub` no están disponibles: `abs(sin(i * 0.040 * 8.0)) * 0.6 + 0.1`
    - _Requirements: 4.1, 4.2, 4.5_

  - [ ]* 4.2 Escribir property test P2 — Amplitud de boca siempre en rango [0.0, 1.0]
    - **Property 2: Amplitud de boca siempre en rango [0.0, 1.0]**
    - **Validates: Requirements 4.2, 4.5, 4.7**
    - Crear `tests/test_tts_engine.py` con `test_mouth_amplitude_range` y `test_fallback_sinusoidal_range`
    - Verificar que tanto la fórmula RMS como el fallback sinusoidal producen valores en [0.0, 1.0]

  - [x] 4.3 Implementar la clase `LipSyncThread` en `tts_engine.py`
    - Constantes: `INTERVAL_S = 0.040`, `NORM_FACTOR = 8000.0`
    - Hilo daemon que itera sobre el array pre-calculado y escribe `mouth_amplitude` en `chibi_state.json` a 25 Hz
    - Método `stop()` que emite `mouth_amplitude = 0.0` dentro de los 40ms siguientes
    - `_write_amplitude()` con try/except silencioso (fail-silent, no interrumpir reproducción)
    - _Requirements: 4.3, 4.4, 4.6, 4.7, 4.8_

  - [x] 4.4 Integrar `LipSyncThread` en el flujo de reproducción de `TTSEngine`
    - Iniciar `LipSyncThread` dentro de los 40ms siguientes al inicio de la reproducción
    - Llamar a `stop()` cuando el audio termina o se recibe señal de stop
    - _Requirements: 4.3, 4.4, 4.6_

- [x] 5. Implementar lectura de Lip-Sync en `cabina_virtual.py`
  - [x] 5.1 Agregar lector de `mouth_amplitude` desde `chibi_state.json` en el loop de renderizado
    - Leer `chibi_state.json` como máximo una vez por frame (60 fps)
    - Usar el valor directamente como target de `ParamMouthOpen` sin escalar
    - Si el archivo no existe o contiene JSON inválido, usar `mouth_amplitude = 0.0` como target sin lanzar excepción
    - Aplicar Lerp a `ParamMouthOpen` con factor `t = min(1.0, dt * 20.0)` para suavizar transiciones
    - _Requirements: 5.1, 5.2, 5.3, 5.4_

- [~] 6. Checkpoint — Verificar Lip-Sync end-to-end
  - Asegurar que todos los tests de `tests/test_tts_engine.py` pasen. Consultar al usuario si hay dudas.

- [x] 7. Implementar historial de conversaciones por sesión en `memory_db.py` y `mongodb_client.py`
  - [x] 7.1 Agregar columna `session_id` a la tabla `conversaciones` en `memory_db.py` y crear tabla `sesiones`
    - Crear tabla `sesiones` con campos: `id`, `inicio`, `fin`, `actividad_principal`, `resumen`, `titulo`, `mensajes_count`
    - Agregar columna `session_id INTEGER DEFAULT NULL` a `conversaciones` con índice `idx_conv_session`
    - Implementar método `start_session()` que inserta en `sesiones` y retorna el `session_id` entero
    - _Requirements: 6.2_

  - [x] 7.2 Actualizar `save_conversation()` y agregar `load_by_session()` en `memory_db.py`
    - Modificar `save_conversation(entrada, respuesta, estado_emocional, session_id)` para incluir `session_id`
    - Implementar `load_by_session(session_id)` que retorna mensajes ordenados por `timestamp` ascendente
    - Implementar `save_to_mongo()` con fallback silencioso a SQLite cuando Atlas no está disponible
    - _Requirements: 6.3, 6.4, 6.5_

  - [ ]* 7.3 Escribir property test P5 — Mensajes de sesión agrupados correctamente (round-trip)
    - **Property 5: Mensajes de sesión agrupados correctamente (round-trip)**
    - **Validates: Requirements 6.3, 6.4, 6.5**
    - Crear `tests/test_memory_db.py` con `test_session_grouping_roundtrip` usando Hypothesis
    - Usar `MemoryDB(":memory:")` para tests en memoria; verificar count y `session_id` de todos los resultados

  - [x] 7.4 Crear índice compuesto `{session_id: 1, timestamp: 1}` en `mongodb_client.py`
    - Agregar método `_crear_indices()` que crea el índice compuesto en la colección `"conversaciones"` si no existe
    - Llamar a `_crear_indices()` durante la inicialización del singleton
    - Implementar `get_collection("conversaciones")` con manejo de reconexión
    - _Requirements: 6.1, 6.6_

- [x] 8. Implementar procesamiento de PDFs con Gemini Vision en `document_intelligence.py`
  - [x] 8.1 Agregar método `_describir_imagen(doc, img_info, n)` en `DocumentIntelligence`
    - Extraer bytes de imagen con `doc.extract_image(xref)`
    - Llamar a `GeminiVision().describe_image_bytes(img_bytes)`
    - Retornar `[Imagen {n}: no disponible]` si `GeminiVision` lanza excepción (fail-silent)
    - _Requirements: 7.2, 7.5_

  - [x] 8.2 Implementar método `_extract_pdf_with_vision(path)` en `DocumentIntelligence`
    - Usar `fitz.open(path)` para abrir el PDF; retornar `[Error: archivo no encontrado o inaccesible: {ruta}]` si falla
    - Por cada página: extraer texto con `page.get_text()` y descripciones de imágenes con `page.get_images()`
    - Concatenar texto e imágenes según las reglas del diseño; incluir solo imágenes si el texto está vacío
    - Truncar el resultado combinado a 15.000 caracteres
    - Fallback a `analizar_documento(path)` si `PyMuPDF` no está instalado
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 7.7_

  - [ ]* 8.3 Escribir property test P8 — Contenido de PDF truncado a máximo 15.000 caracteres
    - **Property 8: Contenido de PDF truncado a máximo 15.000 caracteres**
    - **Validates: Requirements 7.6**
    - Crear `tests/test_document_intelligence.py` con `test_pdf_content_truncated`
    - Verificar que `contenido[:15000]` nunca excede 15.000 caracteres para cualquier entrada de hasta 50.000 chars

- [x] 9. Implementar Function Calling estructurado en `tools.py` y `agent_loop.py`
  - [x] 9.1 Agregar `parsear_tool_call(texto)` y `_validar_params_sin_coordenadas(params)` en `tools.py`
    - Implementar regex `_TOOL_CALL_RE = re.compile(r'TOOL_CALL:\s*(\w+)\s*\(([^)]*)\)', re.IGNORECASE)`
    - `parsear_tool_call()` retorna `(nombre, params_dict)` o `None` si no hay match
    - `_validar_params_sin_coordenadas()` verifica que `params.keys()` no intersecte con `_COORD_PARAMS`
    - Definir `_COORD_PARAMS = frozenset({"x", "y", "pos_x", "pos_y", "coord_x", "coord_y"})`
    - _Requirements: 8.1, 8.2_

  - [ ]* 9.2 Escribir property test P7 — Parser de TOOL_CALL es round-trip correcto
    - **Property 7: Parser de TOOL_CALL es round-trip correcto**
    - **Validates: Requirements 8.2**
    - Crear `tests/test_tools.py` con `test_tool_call_roundtrip` usando Hypothesis
    - Generar nombres de herramienta como identificadores Python válidos y dicts de parámetros string→string
    - Verificar que formatear y luego parsear recupera exactamente el mismo nombre y parámetros

  - [ ]* 9.3 Escribir property test P9 — Herramientas no aceptan parámetros de coordenadas absolutas
    - **Property 9: Herramientas no aceptan parámetros de coordenadas absolutas**
    - **Validates: Requirements 8.1**
    - Agregar `test_tools_no_coord_params` en `tests/test_tools.py`
    - Iterar sobre `get_all_tools()` y verificar que ninguna herramienta tiene claves en `_COORD_PARAMS`

  - [x] 9.4 Actualizar `ejecutar_herramienta()` en `agent_loop.py`
    - Usar `parsear_tool_call()` para extraer nombre y parámetros del texto del LLM
    - Llamar a `_validar_params_sin_coordenadas()` antes de ejecutar; retornar mensaje de error si hay coordenadas
    - Invocar `confirmar_callback` antes de ejecutar herramientas con `critica=True`; bloquear si retorna `False`
    - Retornar `"Che, no conozco la herramienta '{nombre}'. ¿Está bien escrito?"` para herramientas desconocidas
    - Aplicar timeout de 30 segundos; retornar mensaje de cancelación en voseo rioplatense si se excede
    - _Requirements: 8.1, 8.2, 8.3, 8.5, 8.6_

- [~] 10. Checkpoint — Verificar Function Calling y DocumentIntelligence
  - Asegurar que todos los tests de `tests/test_tools.py` y `tests/test_document_intelligence.py` pasen. Consultar al usuario si hay dudas.

- [x] 11. Implementar `ConnectivityChecker` y `SmartRouter` en `brain.py`
  - [x] 11.1 Agregar la clase `ConnectivityChecker` en `brain.py`
    - Verificar internet via TCP a `8.8.8.8:53` con timeout de 2 segundos usando `socket.create_connection`
    - Cachear resultado durante 30 segundos; retornar valor cacheado sin nueva conexión TCP durante ese período
    - Loggear cambio de estado con `[SmartRouter] Conectividad: {online|offline}` solo cuando el estado cambia
    - Retornar `False` si `socket.create_connection` lanza `OSError`
    - _Requirements: 9.1, 9.3, 9.4_

  - [ ]* 11.2 Escribir property test P4 — SmartRouter selecciona Ollama cuando no hay internet
    - **Property 4: SmartRouter selecciona Ollama cuando no hay internet**
    - **Validates: Requirements 9.2**
    - Crear `tests/test_smart_router.py` con `test_router_offline_uses_ollama` usando Hypothesis
    - Mockear `router._connectivity.is_online` para retornar `False`; verificar `decision.engine == "ollama"` para cualquier query

  - [x] 11.3 Actualizar `SmartRouter.analyze()` para consultar `ConnectivityChecker`
    - Agregar `self._connectivity = ConnectivityChecker()` y `self._gemini_blocked_until: float = 0.0` en `__init__`
    - Si `is_online()` retorna `False`, retornar `RoutingDecision("ollama", 1.0, "sin internet → ollama")` inmediatamente
    - Si `time.time() < self._gemini_blocked_until`, retornar `RoutingDecision("ollama", 0.9, "gemini bloqueado → ollama")`
    - Implementar `mark_gemini_failed()` que bloquea Gemini durante 60 segundos
    - _Requirements: 9.2, 9.5_

  - [x] 11.4 Agregar manejo de fallo de Ollama en `SmartRouter`
    - Si Ollama no está disponible (`localhost:11434` rechazado o timeout), retornar mensaje de fallback en voseo rioplatense sin lanzar excepción
    - _Requirements: 9.6_

- [x] 12. Implementar ventana nativa con `pywebview` en `Alisha_IA.py`
  - [x] 12.1 Agregar función `_esperar_servidor(url, timeout_s=15.0)` en `Alisha_IA.py` o módulo auxiliar
    - Intentar `urllib.request.urlopen(url, timeout=1)` en loop hasta que el servidor responda o se agote el timeout
    - Loggear `[Chat] Servidor no disponible tras 15s` y retornar `False` si se agota el timeout
    - _Requirements: 10.4_

  - [x] 12.2 Implementar función `abrir_chat_nativo(url="http://localhost:5000")` en `Alisha_IA.py`
    - Crear hilo daemon con `threading.Thread(target=_run, daemon=True, name="NativeWindow")`
    - Dentro del hilo: llamar a `_esperar_servidor()`; si retorna `False`, salir sin abrir ventana
    - Si `pywebview` está disponible: `pywebview.create_window(title="Alisha IA", url=url, frameless=False)` + `pywebview.start()`
    - Si `pywebview` no está instalado (`ImportError`): `webbrowser.open(url)` + loggear `[Chat] pywebview no disponible — abriendo en navegador`
    - Capturar cualquier otra excepción y loggear el mensaje de error sin relanzar
    - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5_

  - [x] 12.3 Reemplazar `webbrowser.open()` por `abrir_chat_nativo()` en el punto de entrada de `Alisha_IA.py`
    - Localizar la llamada existente a `webbrowser.open("http://localhost:5000")` y reemplazarla
    - Verificar que el hilo daemon no bloquea el loop de renderizado GLFW
    - _Requirements: 10.1, 10.5_

- [x] 13. Crear `conftest.py` y estructura de tests
  - [x] 13.1 Crear `tests/conftest.py` con fixtures compartidos
    - Fixture `memory_db_inmemory` que retorna `MemoryDB(":memory:")` para tests aislados
    - Fixture `mock_connectivity_offline` que parchea `ConnectivityChecker.is_online` para retornar `False`
    - Fixture `sample_audio_bytes` con bytes de audio MP3 mínimo para tests de TTS
    - _Requirements: 6.5, 9.2_

- [~] 14. Checkpoint final — Todos los tests deben pasar
  - Ejecutar `pytest tests/ -v --tb=short` y asegurar que todos los tests pasen.
  - Verificar que los property tests de Hypothesis corren con al menos 100 ejemplos cada uno.
  - Consultar al usuario si hay dudas o si algún test requiere ajustes de configuración del entorno.

## Notes

- Las tareas marcadas con `*` son opcionales y pueden omitirse para un MVP más rápido
- Cada tarea referencia los requisitos específicos para trazabilidad completa
- Los property tests usan Hypothesis (`hypothesis >= 6.0`) con `@settings(max_examples=100)` mínimo
- El principio fail-silent aplica a todos los módulos: capturar excepciones, loggear con prefijo, continuar
- `MemoryDB(":memory:")` permite tests de SQLite completamente aislados sin archivos en disco
- La comunicación entre procesos Live2D ↔ Flask se hace exclusivamente via `chibi_state.json`
- Los tests de `SmartRouter` deben mockear `ConnectivityChecker` para evitar conexiones TCP reales

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "4.1", "7.1", "9.1"] },
    { "id": 1, "tasks": ["1.2", "1.3", "4.2", "7.2", "9.2", "9.3"] },
    { "id": 2, "tasks": ["1.4", "2.1", "2.2", "4.3", "7.3", "7.4", "8.1", "9.4"] },
    { "id": 3, "tasks": ["2.3", "4.4", "8.2", "11.1", "13.1"] },
    { "id": 4, "tasks": ["2.4", "2.5", "5.1", "8.3", "11.2", "11.3"] },
    { "id": 5, "tasks": ["11.4", "12.1"] },
    { "id": 6, "tasks": ["12.2"] },
    { "id": 7, "tasks": ["12.3"] }
  ]
}
```
