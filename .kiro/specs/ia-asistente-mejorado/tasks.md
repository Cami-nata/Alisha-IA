# Tareas de Implementación: ia-asistente-mejorado

## Fase 1: Infraestructura base

- [x] 1. Crear `tts_engine.py` con singleton TTSEngine y cola asíncrona
  - [x] 1.1 Implementar clase `TTSEngine` con patrón singleton (`_instance`)
  - [x] 1.2 Implementar hilo daemon con `queue.Queue` para procesar mensajes FIFO
  - [x] 1.3 Implementar `speak(text)` asíncrono y `speak_sync(text)` bloqueante
  - [x] 1.4 Implementar `set_rate()` y `set_voice()` para configuración
  - [x] 1.5 Agregar función de módulo `speak()` para compatibilidad con `voice.py` existente
  - [x] 1.6 Actualizar `voice.py` para importar `speak` desde `tts_engine`

- [x] 2. Crear `app_discovery.py` con descubrimiento dinámico de aplicaciones
  - [x] 2.1 Implementar búsqueda en `APP_RUTAS` de `config.py` (compatibilidad)
  - [x] 2.2 Implementar búsqueda con `shutil.which()` para apps en PATH
  - [x] 2.3 Implementar búsqueda en rutas estándar (`Program Files`, `AppData`)
  - [x] 2.4 Implementar búsqueda en registro de Windows vía `winreg`
  - [x] 2.5 Implementar caché en memoria y persistencia en `app_cache.json`
  - [x] 2.6 Actualizar `actions.py` para usar `app_discovery.resolver_app()`

- [x] 3. Crear `screen_context.py` con detección inteligente de screenshot
  - [x] 3.1 Implementar `necesita_screenshot(mensaje)` con lista de palabras clave
  - [x] 3.2 Implementar `obtener_contexto_pantalla()` con contexto ligero vía `win32gui`
  - [x] 3.3 Actualizar `ia.py` para usar `screen_context` en lugar de `estado_pantalla()` siempre

## Fase 2: Recordatorios y estado de ánimo

- [x] 4. Crear `reminder_engine.py` con alarmas reales
  - [x] 4.1 Implementar `parsear_tiempo(cuando)` para expresiones en español
  - [x] 4.2 Implementar `programar_recordatorio()` con `threading.Timer`
  - [x] 4.3 Implementar `cancelar_recordatorio(reminder_id)` 
  - [x] 4.4 Implementar `listar_pendientes()` con tiempo restante
  - [x] 4.5 Implementar restauración de timers al arrancar desde `memoria["recordatorios"]`
  - [x] 4.6 Integrar notificaciones de escritorio con `plyer`
  - [x] 4.7 Actualizar `ia.py` para usar `ReminderEngine` al ejecutar acción `recordatorio`

- [x] 5. Actualizar `memory.py` para expiración automática del estado de ánimo
  - [x] 5.1 Agregar `ultima_actualizacion_estado` al guardar estado en `guardar_estado()`
  - [x] 5.2 Implementar `obtener_estado_vigente(perfil)` con lógica de expiración 24h
  - [x] 5.3 Agregar `estado_animo_historial` al modelo de datos de memoria
  - [x] 5.4 Actualizar `ia.py` para usar `obtener_estado_vigente()` en lugar de acceso directo

## Fase 3: Acciones extendidas y Ollama

- [x] 6. Crear `actions_system.py` con acciones de sistema extendidas
  - [x] 6.1 Implementar `controlar_volumen()` con `pycaw`
  - [x] 6.2 Implementar `reproducir_musica()` con teclas multimedia y apertura de apps
  - [x] 6.3 Implementar `buscar_archivo()` con límite de 10 resultados
  - [x] 6.4 Implementar `controlar_brillo()` con `screen-brightness-control`
  - [x] 6.5 Actualizar `obtener_info_sistema()` en `actions.py` con CPU% y RAM%
  - [x] 6.6 Agregar nuevas acciones al `VALID_ACTIONS` en `config.py`
  - [x] 6.7 Actualizar el prompt de Ollama en `ollama.py` para incluir nuevas acciones
  - [x] 6.8 Actualizar `ejecutar()` en `ia.py` para despachar nuevas acciones

- [x] 7. Actualizar `ollama.py` con reintentos y backoff exponencial
  - [x] 7.1 Implementar `enviar_a_ollama_con_reintentos()` con `max_reintentos=3`
  - [x] 7.2 Implementar backoff exponencial: 1s, 2s, 4s entre intentos
  - [x] 7.3 Distinguir errores recuperables (timeout, conexión) de irrecuperables
  - [x] 7.4 Actualizar `preguntar_ia()` para usar la función con reintentos
  - [x] 7.5 Ampliar memoria de contexto en el prompt de 5 a 10 entradas recientes

## Fase 4: Identidad y GUI

- [x] 8. Crear `identity_evolution.py` con evolución gradual de identidad
  - [x] 8.1 Actualizar `ia_identidad.json` con campos `version`, `rasgos`, `tono_preferido`, timestamps
  - [x] 8.2 Implementar `evaluar_evolucion()` que actúa cada 20 interacciones
  - [x] 8.3 Implementar `forzar_evolucion()` para evolución inmediata
  - [x] 8.4 Integrar en el loop principal de `ia.py` tras cada interacción

- [x] 9. Crear `gui.py` con interfaz tkinter opcional
  - [x] 9.1 Implementar ventana principal con área de chat (ScrolledText)
  - [x] 9.2 Implementar campo de entrada y botón de envío
  - [x] 9.3 Implementar diferenciación visual usuario vs asistente (colores)
  - [x] 9.4 Integrar con el loop principal de `ia.py` como modo alternativo
  - [x] 9.5 Implementar cierre limpio (TTS detenido, timers cancelados)
  - [x] 9.6 Mostrar errores en el área de chat en lugar de solo en terminal

## Fase 5: Testing y ajustes finales

- [ ] 10. Escribir tests unitarios
  - [ ] 10.1 `test_app_discovery.py`: resolución, caché, apps inexistentes
  - [ ] 10.2 `test_reminder_engine.py`: parseo de tiempo, timers, restauración
  - [ ] 10.3 `test_screen_context.py`: detección de palabras clave, contexto ligero
  - [ ] 10.4 `test_memory.py`: expiración de estado, truncado de historial (50 JSON / 500 MongoDB)
  - [ ] 10.5 `test_ollama_retries.py`: reintentos con mock de requests
  - [ ] 10.6 `test_emotion_engine.py`: transiciones de estado, instrucciones de tono, singleton
  - [ ] 10.7 `test_mongodb_client.py`: disponibilidad, fallback a JSON, reconexión
  - [ ] 10.8 `test_voice_simplified.py`: verificar que speak() existe y que escuchar_voz/elegir_modo_entrada no existen

- [x] 11. Actualizar `config.py` y dependencias
  - [x] 11.1 Agregar nuevas acciones a `VALID_ACTIONS`
  - [x] 11.2 Agregar constantes MongoDB: `MONGO_URI`, `MONGO_DB`, `MONGO_MAX_HISTORIAL=500`
  - [x] 11.3 Crear `requirements.txt` con todas las dependencias (nuevas y existentes, sin `speech_recognition`)
  - [x] 11.4 Verificar compatibilidad de imports en todos los módulos actualizados

## Fase 6: IA emocional y humana

- [x] 12. Crear `emotion_engine.py` con motor de emociones de la IA
  - [x] 12.1 Implementar clase `EmotionEngine` con patrón singleton
  - [x] 12.2 Definir los 6 estados emocionales: alegría, curiosidad, entusiasmo, preocupación, nostalgia, neutral
  - [x] 12.3 Implementar `obtener_estado_actual()` con estado, intensidad y descripción
  - [x] 12.4 Implementar `actualizar_estado(interaccion)` con lógica de transición gradual
  - [x] 12.5 Implementar `obtener_instruccion_tono()` para inyectar en el prompt del sistema
  - [x] 12.6 Implementar `puede_iniciar_conversacion()` y `generar_inicio_conversacion()`
  - [x] 12.7 Persistir estado emocional en colección `identidad` (MongoDB) o `ia_identidad.json` (fallback)
  - [x] 12.8 Integrar `EmotionEngine` en `ollama.py`: incluir instrucción de tono en el prompt del sistema
  - [x] 12.9 Integrar `EmotionEngine` en el loop principal de `ia.py`: actualizar estado tras cada interacción

- [x] 13. Actualizar prompt del sistema en `ollama.py` para personalidad emocional
  - [x] 13.1 Implementar `construir_prompt_sistema(identidad, emocion, perfil)` que genera prompt rico
  - [x] 13.2 Incluir instrucciones de lenguaje coloquial en español, contracciones, expresiones naturales
  - [x] 13.3 Incluir referencias a conversaciones pasadas del perfil del usuario
  - [x] 13.4 Incluir frases características de la IA según su identidad
  - [x] 13.5 Actualizar `preguntar_ia()` para usar el nuevo prompt emocional
  - [x] 13.6 Actualizar `_generar_identidad()` para incluir campos emocionales: `estado_emocional_base`, `frases_caracteristicas`, `humor_activo`, `puede_iniciar`

## Fase 7: Simplificación de voice.py (solo TTS)

- [x] 14. Simplificar `voice.py` para eliminar reconocimiento de voz
  - [x] 14.1 Eliminar import de `speech_recognition` y toda lógica relacionada
  - [x] 14.2 Eliminar función `elegir_modo_entrada()`
  - [x] 14.3 Eliminar función `escuchar_voz()`
  - [x] 14.4 Mantener solo `speak(text)` y la inicialización del motor TTS
  - [x] 14.5 Actualizar `ia.py`: eliminar `modo_voz`, `idioma`, y toda la lógica de voz del loop principal
  - [x] 14.6 Actualizar `ia.py`: el loop siempre usa `input("Tú: ")` sin condiciones de modo

## Fase 8: MongoDB con fallback a JSON

- [x] 15. Crear `mongodb_client.py` con cliente MongoDB singleton
  - [x] 15.1 Implementar clase `MongoDBClient` con patrón singleton
  - [x] 15.2 Implementar conexión a `mongodb://localhost:27017/ia_asistente`
  - [x] 15.3 Implementar `is_available()` con ping sin lanzar excepciones
  - [x] 15.4 Implementar `get_collection(nombre)` para las 5 colecciones
  - [x] 15.5 Crear índice automático en `historial` por campo `fecha` descendente
  - [x] 15.6 Implementar función de módulo `get_db()` que retorna instancia o None

- [x] 16. Actualizar `memory.py` para usar MongoDB con fallback a JSON
  - [x] 16.1 Actualizar `cargar_memoria()`: intentar MongoDB primero, fallback a JSON
  - [x] 16.2 Actualizar `guardar_memoria()`: escribir en MongoDB si disponible, sino JSON
  - [x] 16.3 Actualizar `agregar_memoria()`: insertar en colección `historial` de MongoDB; purgar si >500 entradas
  - [x] 16.4 Actualizar `cargar_identidad()` / `guardar_identidad()`: usar colección `identidad`
  - [x] 16.5 Actualizar `guardar_recordatorio()`: usar colección `recordatorios`
  - [x] 16.6 Actualizar `guardar_perfil()` / `guardar_estado()`: usar colección `perfil`
  - [x] 16.7 Mantener interfaz pública idéntica (mismas funciones, mismos parámetros)
  - [x] 16.8 Loguear aviso cuando se activa fallback JSON: "MongoDB no disponible, usando fallback JSON"

## Fase 9: Navegación web real con Playwright

- [x] 17. Crear `browser_agent.py` con automatización de navegador
  - [x] 17.1 Implementar clase `BrowserAgent` con patrón singleton usando `playwright.sync_api`
  - [x] 17.2 Implementar `abrir_url(url)` — abre o navega a una URL en el navegador activo
  - [x] 17.3 Implementar `buscar_en_google(query)` — abre Google y escribe la búsqueda
  - [x] 17.4 Implementar `click_elemento(selector_o_texto)` — hace click por selector CSS o texto visible
  - [x] 17.5 Implementar `escribir_en_campo(selector, texto)` — llena un campo de formulario
  - [x] 17.6 Implementar `leer_pagina()` — extrae el texto visible de la página actual
  - [x] 17.7 Implementar `screenshot_pagina(nombre)` — captura la página actual
  - [x] 17.8 Implementar `cerrar_navegador()` — cierra el navegador limpiamente
  - [x] 17.9 Implementar detección automática de navegador disponible (Chrome → Edge → Firefox)
  - [x] 17.10 Manejar errores de navegación sin crashear (página no encontrada, timeout, etc.)

- [x] 18. Agregar acciones de navegación al sistema
  - [x] 18.1 Agregar `navegar_web`, `buscar_web`, `click_web`, `escribir_web`, `leer_web` a `VALID_ACTIONS` en `config.py`
  - [x] 18.2 Actualizar `_validar_accion()` en `ollama.py` para los nuevos tipos de acción web
  - [x] 18.3 Actualizar `ejecutar()` en `ia.py` para despachar acciones web a `BrowserAgent`
  - [x] 18.4 Actualizar el prompt de Ollama para incluir las nuevas acciones web con ejemplos
  - [x] 18.5 Instalar Playwright: agregar `playwright` a `requirements.txt` y documentar `playwright install chromium`

## Fase 10: Conocimientos de informática y programación en el prompt

- [x] 19. Actualizar identidad y prompt del sistema para conocimientos técnicos
  - [x] 19.1 Actualizar `_generar_identidad()` en `ollama.py` para incluir `conocimientos_tecnicos` en la identidad generada
  - [x] 19.2 Actualizar `construir_prompt_sistema()` para incluir sección de expertise técnico: programación, debugging, algoritmos, sistemas operativos, redes, bases de datos
  - [x] 19.3 Agregar instrucción al prompt: la IA puede explicar código, revisar errores, sugerir soluciones, escribir scripts, y enseñar conceptos de informática
  - [x] 19.4 Agregar acción `ejecutar_codigo` a `VALID_ACTIONS` — ejecuta snippets Python en un entorno seguro (subprocess con timeout)
  - [x] 19.5 Implementar `ejecutar_codigo_seguro(codigo, timeout=10)` en `actions_system.py` con sandbox básico
  - [x] 19.6 Actualizar `ia_identidad.json` para incluir campo `expertise`: lista de áreas de conocimiento técnico

## Fase 11: Autoconciencia — la IA sabe lo que sabe

- [ ] 20. Crear `self_awareness.py` — módulo de autoconciencia del asistente
  - [ ] 20.1 Implementar `cargar_aprendizaje_rl() -> dict` — lee `models/self_awareness.json` del proyecto Pygame RL si existe
  - [ ] 20.2 Implementar `obtener_capacidades() -> dict` — combina habilidades RL + capacidades del asistente (acciones disponibles, expertise técnico)
  - [ ] 20.3 Implementar `sabe_hacer(tarea: str) -> tuple[bool, str]` — retorna (puede_hacerlo, explicacion) basado en capacidades conocidas
  - [ ] 20.4 Implementar `obtener_limitaciones() -> list[str]` — lista de cosas que la IA sabe que no puede hacer bien todavía
  - [ ] 20.5 Integrar en `construir_prompt_sistema()` de `ollama.py`: incluir sección de autoconciencia con capacidades y limitaciones conocidas
  - [ ] 20.6 Integrar en `ia.py`: cargar autoconciencia al arrancar y actualizar tras cada sesión de entrenamiento RL
