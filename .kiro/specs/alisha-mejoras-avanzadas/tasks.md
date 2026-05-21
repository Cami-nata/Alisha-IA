# Plan de Implementación: alisha-mejoras-avanzadas

## Overview

Implementación incremental de las mejoras avanzadas de Alisha en Python. Cada tarea construye sobre la anterior, comenzando por la capa de datos y emociones, luego visión y automatización, después interfaz y comunicación, y finalmente el orquestador principal. El lenguaje de implementación es **Python** con PyQt6.

## Tareas

- [ ] 1. Infraestructura base: MongoDB Client y persistencia dual
  - [ ] 1.1 Implementar `mongodb_client.py` con conexión, fallback JSON y cola de sincronización
    - Clase `MongoDBClient` con métodos `conectar()`, `guardar()`, `buscar()`, `sincronizar_cola()`
    - Modo fallback automático a archivos JSON cuando MongoDB no está disponible
    - Reconexión en background cada 5 minutos usando `threading.Timer`
    - Locks de threading para escrituras concurrentes (Requisito 21.5)
    - _Requisitos: 10.1, 10.2, 10.3, 10.4, 10.5_

  - [ ] 1.2 Implementar resolución de conflictos y sincronización
    - Función `resolver_conflictos(local, remoto)` con regla de timestamp más reciente
    - Fusión de campos lista (`gustos`, `tags`, `temas`) y máximo en campos numéricos
    - Notificación al usuario en conflictos irresolubles
    - _Requisitos: 10.6, 10.7_

  - [ ]* 1.3 Escribir property test para resolución de conflictos
    - **Property 9: Resolución de conflictos por timestamp más reciente**
    - **Valida: Requisito 10.6**

  - [ ]* 1.4 Escribir tests unitarios para MongoDB Client
    - Usar `mongomock` para tests sin servidor real
    - Casos: fallback activado, sincronización de cola, modo reconexión
    - _Requisitos: 10.1, 10.2, 10.4_

- [ ] 2. Motor de emociones y cognición (`emotion_engine.py`)
  - [ ] 2.1 Implementar núcleo del `EmotionEngine`: estado, dopamina y análisis NLP
    - Clase `EmotionEngine` con campos: `estado`, `intensidad`, `dopamina`, `cansancio`, `energia`
    - Análisis de sentimiento con TextBlob (primario) y VADER (fallback)
    - Extracción de polaridad, subjetividad y clasificación en positivo/neutral/negativo
    - Historial de últimos 10 sentimientos para detección de tendencias
    - Campo `"pensamiento"` en el JSON de respuesta
    - _Requisitos: 1.1, 1.6, 2.1, 2.2, 2.3, 2.4, 2.5, 2.6_

  - [ ]* 2.2 Escribir property test para campo "pensamiento"
    - **Property 5: JSON de respuesta siempre contiene campo "pensamiento"**
    - **Valida: Requisito 1.6**

  - [ ] 2.3 Implementar sistema de dopamina no lineal con curva de saciedad
    - Fórmula: `Δdopamina = 0.15 * (1 - dopamina_actual)^0.5`
    - Cap de saciedad: cuando `dopamina >= 0.95`, próximos 5 éxitos al 50%
    - Métodos `registrar_exito_rl()` y `registrar_fracaso_rl()`
    - _Requisitos: 1.2, 1.8_

  - [ ]* 2.4 Escribir property test para curva de saciedad de dopamina
    - **Property 1: Curva de saciedad de dopamina es decreciente**
    - **Valida: Requisitos 1.2, 1.8**

  - [ ] 2.5 Implementar sistema de fatiga temporal con multiplicador nocturno
    - Función `calcular_fatiga(horas_activas, interacciones_hora, hora_actual)`
    - Multiplicador nocturno 1.3x para horas 00:00-05:59
    - Recuperación pasiva: -10 puntos/hora tras 60 min de inactividad
    - Reset de fatiga al cerrar o entrar en IDLE
    - _Requisitos: 1.3, 1.4, 3.1, 3.2, 3.6, 3.7_

  - [ ]* 2.6 Escribir property test para multiplicador nocturno de fatiga
    - **Property 2: Multiplicador nocturno de fatiga**
    - **Valida: Requisitos 1.3, 3.2**

  - [ ]* 2.7 Escribir property test para fórmula de fatiga base
    - **Property 3: Fórmula de fatiga base**
    - **Valida: Requisito 3.1**

  - [ ] 2.8 Implementar errores por cansancio y ajuste de respuestas
    - Función `aplicar_errores_cansancio(texto, fatiga)` con typos y omisión de mayúsculas
    - Reducción de longitud de respuesta al 80% cuando fatiga > 50%
    - Typos: 1 cada 50 palabras cuando fatiga > 70%
    - Omisión de mayúscula inicial en 30% de oraciones cuando fatiga > 70%
    - _Requisitos: 1.5, 3.3, 3.4, 3.5_

  - [ ]* 2.9 Escribir property test para errores por cansancio
    - **Property 4: Errores por cansancio son proporcionales a la fatiga**
    - **Valida: Requisitos 1.5, 3.4**

  - [ ] 2.10 Implementar persistencia de estado emocional y personalidad
    - Carga desde `ia_identidad.json` con rasgos de personalidad de Alisha
    - Guardado/carga de estado en MongoDB colección `identidad`
    - Método `cargar_desde_identidad()` y `persistir_estado()`
    - _Requisitos: 1.7, 22.1, 22.2_

  - [ ]* 2.11 Escribir property test para persistencia de estado emocional
    - **Property 6: Persistencia de estado emocional es un round-trip**
    - **Valida: Requisitos 1.7, 10.1**

- [ ] 3. Checkpoint — Verificar que EmotionEngine y MongoDBClient funcionan correctamente
  - Asegurar que todos los tests pasan, consultar al usuario si hay dudas.

- [ ] 4. Memoria jerárquica (`memory_hierarchy.py`)
  - [ ] 4.1 Implementar `MemoryHierarchy` con clasificación automática de importancia
    - Clase `MemoryHierarchy` con métodos `agregar_memoria()`, `clasificar_importancia()`, `buscar_por_nivel()`
    - Patrones regex para nivel 10 (datos personales), nivel 8 (preferencias), nivel 5 (eventos recientes)
    - Memorias de nivel 10 marcadas como permanentes
    - _Requisitos: 8.1, 8.2, 8.3, 8.4, 8.5_

  - [ ]* 4.2 Escribir property test para clasificación automática de importancia
    - **Property 8: Clasificación automática de datos personales y preferencias**
    - **Valida: Requisitos 8.1, 8.2, 8.3, 8.4**

  - [ ] 4.3 Implementar archivado de memorias antiguas y memorias permanentes
    - Función `archivar_memorias_antiguas()`: memorias nivel < 5 con > 30 días → `archivada=True`
    - Memorias nivel 10 nunca se archivan ni eliminan
    - Ajuste manual de nivel por el usuario
    - Comando para listar memorias permanentes
    - _Requisitos: 8.5, 8.6, 8.7, 8.8_

  - [ ]* 4.4 Escribir property test para permanencia de memorias nivel 10
    - **Property 7: Memorias de nivel 10 son permanentes**
    - **Valida: Requisito 8.5**

  - [ ]* 4.5 Escribir property test para archivado de memorias antiguas
    - **Property 12: Memorias antiguas de baja importancia se archivan**
    - **Valida: Requisito 8.6**

  - [ ] 4.6 Implementar colección de hitos y celebraciones
    - Métodos `crear_hito()`, `listar_hitos()`, `verificar_aniversarios()`
    - Detección automática de hitos en conversación
    - Estadísticas de hitos: total, categorías, tiempo promedio
    - _Requisitos: 11.1, 11.2, 11.3, 11.5, 11.6_

  - [ ] 4.7 Implementar proceso de sueño (`Sleep_Process`)
    - Clase `SleepProcess` que corre en QThread separado
    - Generación de resumen del día con Llama 3
    - Consolidación de memorias nivel < 5 relacionadas (similitud coseno > 0.7)
    - Incremento de nivel para memorias mencionadas > 3 veces
    - Guardado en colección `daily_summaries` y reset de fatiga
    - _Requisitos: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 9.7, 9.8_

- [ ] 5. Checkpoint — Verificar memoria jerárquica y proceso de sueño
  - Asegurar que todos los tests pasan, consultar al usuario si hay dudas.

- [ ] 6. Visión y automatización (`screen_vision.py`, `safe_click.py`)
  - [ ] 6.1 Implementar `ScreenVision` con OCR y escáner de escritorio
    - Integración de `pytesseract` con preprocesamiento (escala de grises, binarización, reducción de ruido)
    - OCR en español e inglés con umbral de confianza 70%
    - Escaneo del Escritorio cada 30 minutos, clasificación de archivos en categorías
    - Detección de desorden (> 15 archivos) y estado "ordenado" (< 10 archivos)
    - _Requisitos: 4.1, 4.2, 4.4, 6.1, 6.2, 6.3, 6.4, 6.5, 6.6_

  - [ ] 6.2 Implementar organización automática de archivos y copia al portapapeles
    - Creación de carpetas por categoría y movimiento de archivos
    - Contador de archivos organizados en perfil del usuario
    - Copia de texto OCR al portapapeles
    - _Requisitos: 4.3, 4.5, 4.6, 4.7, 6.7_

  - [ ] 6.3 Implementar `SafeClick` con template matching de OpenCV
    - Captura de ventana activa antes de cada clic
    - Template matching con umbral de confianza 80%
    - Guardado de capturas de auditoría en `logs/safe_clicks/` con timestamp
    - Soporte de offset relativo al elemento encontrado
    - _Requisitos: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 7.7_

  - [ ]* 6.4 Escribir tests unitarios para ScreenVision y SafeClick
    - Test de clasificación de archivos por categoría
    - Test de umbral de confianza OCR
    - Test de rechazo de clic cuando template no se encuentra
    - _Requisitos: 4.2, 6.4, 7.3_

- [ ] 7. Contexto inteligente y percepción de audio (`context_intelligence.py`, `audio_perception.py`)
  - [ ] 7.1 Implementar `ContextIntelligence` con detección de app activa
    - Detección con `win32gui.GetForegroundWindow()`
    - Lógica por app: VS Code (inactividad 5 min), Canva (modo validación), YouTube (OCR título), Chrome/Edge (URL + título)
    - Historial de apps con timestamps en MongoDB y estadísticas semanales
    - Registro de apps desconocidas para aprendizaje
    - _Requisitos: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7, 5.8_

  - [ ] 7.2 Implementar `AudioPerception` en thread de baja prioridad
    - Monitoreo de audio del sistema (loopback) con polling cada 10 segundos
    - Detección de tipo: música, reunión (Zoom/Teams/Meet/Discord), video (YouTube/Netflix/VLC), silencio
    - Identificación de título/artista (ACRCloud o metadatos del reproductor)
    - JSON de contexto: `{"audio_activo": bool, "tipo": str, "titulo": str, "artista": str}`
    - Actualización de `perfil["gustos_musicales"]` en MongoDB
    - _Requisitos: 25.1, 25.2, 25.3, 25.4, 25.5, 25.7, 25.8, 25.9, 25.10_

  - [ ]* 7.3 Escribir tests unitarios para ContextIntelligence y AudioPerception
    - Test de detección de apps conocidas (VS Code, Canva, YouTube)
    - Test de formato del JSON de contexto de audio
    - _Requisitos: 5.1, 25.5_

- [ ] 8. Control de aplicaciones y navegadores (`pc_controller.py`, `browser_controller.py`)
  - [ ] 8.1 Implementar `PCController` con descubrimiento dinámico de apps
    - Escaneo de `Program Files`, `Program Files (x86)`, `AppData\Local`, `AppData\Roaming` y registro de Windows
    - Índice actualizable con nombre, ruta y categoría; persistencia en MongoDB colección `app_cache`
    - Búsqueda fuzzy por nombre parcial con confirmación antes de abrir
    - Listado de apps agrupadas por categoría
    - _Requisitos: 23.1, 23.2, 23.3, 23.4, 23.8_

  - [ ] 8.2 Implementar gestión de procesos en `PCController`
    - Cierre limpio de apps (graceful → force kill si no responde en 5s)
    - Detección de apps abiertas y sus estados (minimizada, maximizada, en foco)
    - Cambio de foco entre apps abiertas por nombre
    - _Requisitos: 23.5, 23.6, 23.7_

  - [ ] 8.3 Implementar `BrowserController` con Playwright
    - Detección automática de navegadores instalados (Chrome, Edge, Firefox, Brave, Opera)
    - Abrir URL, nueva pestaña, cerrar pestaña, navegar entre pestañas
    - Escribir en campos de formulario, clic por texto/selector CSS/posición relativa
    - Scroll (arriba, abajo, a elemento específico)
    - _Requisitos: 24.1, 24.2, 24.3, 24.4, 24.6, 24.7_

  - [ ] 8.4 Implementar lectura de contenido web y formularios completos en `BrowserController`
    - Leer y resumir contenido de la página actual
    - Rellenar formularios completos (login, búsqueda, registro) con autorización del usuario
    - Búsqueda en buscador predeterminado del usuario
    - Copiar texto seleccionado al portapapeles
    - Fallback a `pyautogui` si Playwright no está disponible
    - _Requisitos: 24.5, 24.8, 24.9, 24.10_

  - [ ]* 8.5 Escribir tests unitarios para PCController y BrowserController
    - Test de búsqueda fuzzy de apps
    - Test de detección de navegadores instalados
    - _Requisitos: 23.3, 24.1_

- [ ] 9. Seguridad (`safety_guard.py`)
  - [ ] 9.1 Implementar `SafetyGuard` con validación AST y lista de comandos peligrosos
    - Lista completa `COMANDOS_PELIGROSOS` con os.remove, shutil, subprocess, exec, eval, etc.
    - Clase `DangerousCodeVisitor(ast.NodeVisitor)` para detección de ofuscación
    - Función `validar_codigo(codigo)` que retorna `False` y registra en log si detecta peligro
    - Log de auditoría en `logs/dangerous_commands.log` con formato timestamp + estado + comando
    - _Requisitos: 20.1, 20.2, 20.3, 20.4, 20.6, 20.7_

  - [ ]* 9.2 Escribir property test para Safety Guard
    - **Property 11: Safety Guard rechaza todos los comandos peligrosos**
    - **Valida: Requisitos 20.1, 20.2, 20.4**

  - [ ] 9.3 Implementar Kill Switch global (Ctrl+Alt+K)
    - Registro de hotkey global con librería `keyboard`
    - Al activarse: `kill_switch_activo = True`, señal STOP a todos los threads
    - Cancelar acciones pendientes en PCController, detener TTS, cerrar Playwright
    - Notificación de escritorio y registro en `logs/kill_switch.log`
    - Reanudar operaciones solo con acción manual del usuario
    - _Requisitos: 19.1, 19.2, 19.3, 19.4, 19.5, 19.6, 19.7, 19.8_

  - [ ]* 9.4 Escribir tests unitarios para SafetyGuard
    - Test de detección de comandos directos y ofuscados via AST
    - Test de activación del kill switch y limpieza de estado
    - _Requisitos: 20.2, 20.4, 19.2_

- [ ] 10. Checkpoint — Verificar seguridad, visión y automatización
  - Asegurar que todos los tests pasan, consultar al usuario si hay dudas.

- [ ] 11. Comunicación en tiempo real (`websocket_server.py`, `tts_engine.py`)
  - [ ] 11.1 Implementar `WebSocketServer` en QThread separado
    - Servidor en puerto 8765 con `websockets`
    - Tipos de mensajes: `emotion_change`, `text_bubble`, `animation_trigger`, `micro_expression`, `state_update`
    - Broadcast a todos los clientes conectados
    - Reconexión automática con backoff, máx 10 intentos
    - _Requisitos: 12.1, 12.2, 12.3, 12.7, 12.8_

  - [ ]* 11.2 Escribir property test para mensajes WebSocket
    - **Property 10: Mensajes WebSocket reflejan el estado emocional actual**
    - **Valida: Requisito 12.2**

  - [ ] 11.3 Implementar `TTSEngine` en QThread separado
    - Cola de mensajes con procesamiento asíncrono
    - Cancelación al llegar nuevo mensaje
    - Sincronización de animaciones de boca con audio generado
    - Fallback de pyttsx3 → gTTS + pygame
    - Ajuste de velocidad/tono según estado emocional y fatiga (−15% velocidad si fatiga > 90%)
    - Reducción de volumen al 20% o silencio cuando el usuario está en reunión
    - _Requisitos: 17.1, 17.2, 17.3, 17.4, 17.5, 17.6, 17.7, 25.6_

  - [ ]* 11.4 Escribir tests unitarios para TTSEngine y WebSocketServer
    - Test de encolado y cancelación de TTS
    - Test de formato de mensajes WebSocket por tipo
    - _Requisitos: 17.2, 17.3, 12.3_

- [ ] 12. Transcripción de reuniones (`audio_listener.py`)
  - [ ] 12.1 Implementar `AudioListener` con Whisper en thread separado
    - Captura de audio en chunks de `CHUNK_SECONDS=3`
    - Transcripción con Whisper (local o API)
    - Guardado en `transcripciones/` con timestamp
    - Marca de pausa tras silencio > 5 segundos
    - Detección de cambio de hablante
    - Resumen automático al terminar la reunión con Llama 3
    - _Requisitos: 18.1, 18.2, 18.3, 18.4, 18.5, 18.6, 18.7_

  - [ ]* 12.2 Escribir tests unitarios para AudioListener
    - Test de inserción de marca de pausa tras silencio
    - Test de formato de archivo de transcripción
    - _Requisitos: 18.3, 18.4_

- [ ] 13. Interfaz Live2D (`live2d_window.py`)
  - [ ] 13.1 Implementar `Live2DWindow` con expresiones y micro-expresiones
    - Conexión al WebSocketServer al iniciar
    - Mapeo de emociones a parámetros Live2D (tabla del diseño)
    - Soporte de emoción primaria + secundaria simultáneas
    - Ciclo de micro-expresiones idle cada 5-10 segundos aleatorio
    - Animaciones específicas: cosquillas, bostezo, parpadeo, celebración, cabeceo
    - _Requisitos: 12.4, 12.5, 12.6, 13.1, 13.2, 13.3, 13.4, 13.5, 13.6_

  - [ ] 13.2 Implementar modo concentración con opacidad dinámica
    - Detección de apps de trabajo maximizadas
    - Reducción de opacidad al 30% automáticamente; restauración al 100% al acercar cursor
    - Lista configurable de apps que activan modo concentración
    - Seguimiento del cursor con la mirada del modelo
    - _Requisitos: 14.1, 14.2, 14.3, 14.4, 14.5, 14.6, 14.7_

  - [ ] 13.3 Implementar edge snapping y persistencia de posición
    - Función `calcular_snap(pos, screen_rect, window_size)` con umbral de 20px
    - Snap a 4 bordes y 4 esquinas, soporte multi-monitor
    - Persistencia de posición en `chibi_prefs.json`
    - Guías visuales al arrastrar
    - _Requisitos: 15.1, 15.2, 15.3, 15.4, 15.5, 15.6, 15.7_

  - [ ] 13.4 Implementar física interactiva y reacciones al toque
    - Clic en cabeza → animación cosquillas + sonido de risa
    - Clic en cuerpo → animación saludo o gesto aleatorio
    - Arrastre con física de rebote suave al soltar
    - Doble clic → menú de acciones rápidas
    - Clic sostenido → tooltip con estado actual
    - _Requisitos: 16.1, 16.2, 16.3, 16.4, 16.5, 16.6, 16.7_

  - [ ]* 13.5 Escribir tests unitarios para Live2DWindow
    - Test de mapeo de emoción a parámetros Live2D correctos
    - Test de cálculo de snap a bordes y esquinas
    - _Requisitos: 12.5, 15.2_

- [ ] 14. Dashboard web (`web/`)
  - [ ] 14.1 Implementar servidor FastAPI con endpoints REST
    - `GET /api/estado`, `GET /api/memorias`, `GET /api/historial`, `GET /api/hitos`
    - `GET /api/perfil`, `POST /api/memoria/{id}/nivel`, `GET /api/daily_summary`
    - `POST /api/kill_switch`, `GET /api/stats/apps`
    - Servidor en `http://localhost:8080` en QThread separado
    - _Requisitos: 12.1 (web), 8.8, 11.7_

  - [ ] 14.2 Implementar frontend del dashboard
    - `web/index.html` con gauges de dopamina, energía y fatiga
    - `web/static/js/websocket.js` con cliente WebSocket que actualiza gauges en tiempo real
    - Indicador de estado de conexión MongoDB
    - Historial de conversación y panel de memorias
    - _Requisitos: 10.8, 12.2_

  - [ ]* 14.3 Escribir tests unitarios para endpoints FastAPI
    - Test de respuesta correcta de `/api/estado`
    - Test de actualización de nivel de memoria via POST
    - _Requisitos: 8.7, 10.8_

- [ ] 15. Orquestador principal (`main.py`)
  - [ ] 15.1 Implementar `main.py` con orden de inicialización y QThreads
    - Orden crítico: identidad → EmotionEngine → MongoDB → MemoryHierarchy → SafetyGuard → WebSocketServer → TTSEngine → ContextIntelligence → ScreenVision/SafeClick → Live2DWindow → FastAPI
    - Clase `BaseWorkerThread(QThread)` con `error_signal` para manejo de errores global
    - Reinicio automático de threads críticos (ChatThread, LlamaThread, DBThread)
    - _Requisitos: 21.1, 21.2, 21.3, 21.6, 21.7_

  - [ ] 15.2 Implementar watchdog de threads bloqueados
    - `QTimer` que llama `watchdog_check()` cada 30 segundos
    - Heartbeats por thread; si último heartbeat > 30s → `thread.terminate()` + reinicio
    - Registro de eventos de watchdog en `logs/errors/`
    - _Requisitos: 21.8_

  - [ ] 15.3 Integrar AudioPerception con TTS y modo silencioso
    - Cuando AudioPerception detecta reunión → TTS reduce volumen al 20% o silencio
    - Cuando AudioPerception detecta cambio de canción → actualizar contexto
    - Respuesta a "¿qué estoy escuchando?" usando datos de AudioPerception
    - _Requisitos: 25.3, 25.6, 25.7, 25.9_

  - [ ]* 15.4 Escribir tests de integración del orquestador
    - Test de orden de inicialización correcto
    - Test de reinicio de thread tras error simulado
    - Test de watchdog detectando thread bloqueado
    - _Requisitos: 21.7, 21.8_

- [ ] 16. Checkpoint final — Asegurar que todos los tests pasan
  - Ejecutar suite completa de pytest + Hypothesis, consultar al usuario si hay dudas.

## Notas

- Las tareas marcadas con `*` son opcionales y pueden omitirse para un MVP más rápido
- Cada tarea referencia requisitos específicos para trazabilidad
- Los property tests usan Hypothesis con `max_examples=100` según el diseño
- Los tests de integración usan `mongomock`, `pytest-asyncio` y `unittest.mock`
- `CHUNK_SECONDS=3` es constante global para AudioListener (Requisito 21.4)
- El Kill Switch (Ctrl+Alt+K) tiene prioridad máxima y debe funcionar en cualquier estado del sistema
