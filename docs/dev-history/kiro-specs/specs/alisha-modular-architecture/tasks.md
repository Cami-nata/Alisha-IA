# Implementation Plan

- [x] 1. Crear estructura de directorios y __init__.py vacíos
  - Crear `core/__init__.py`, `memory/__init__.py`, `personality/__init__.py`, `avatar/__init__.py`, `vision/__init__.py`, `tools/__init__.py`, `services/__init__.py`, `integrations/__init__.py`, `web/__init__.py`, `web/routes/__init__.py`, `config/__init__.py` — todos vacíos
  - El sistema debe seguir funcionando con los archivos en el root después de esta tarea
  - _Requirements: 1_

- [x] 2. Crear config/ centralizado
  - Crear `config/env_loader.py` con función `load_env() -> None` que carga `.env` con python-dotenv
  - Crear `config/settings.py` con todas las variables de `config.py`: `BASE_DIR`, `DATA_DIR`, `OLLAMA_URL`, `MODEL`, `ELEVENLABS_API_KEY`, `LIVE2D_MODEL_PATH`, `MONGO_URI`, `SAFE_MODE`, `CONFIRMAR_ACCIONES`, `ACCIONES_PELIGROSAS`, `VALID_ACTIONS`, `APP_RUTAS`, `POWER_COMMANDS`, `IDENTIDAD_FILE`, `MEMORY_FILE`, `LOG_FILE`, `FRECUENCIA_OBSERVACION`
  - Crear `config/constants.py` con constantes inmutables: `STATE_FILE`, `CYCLE_INTERVAL_S=5.0`, `HEARTBEAT_INTERVAL_S=30.0`, `FILE_CHANGE_WINDOW_S=30.0`, `IDLE_TRANSITION_S=2.0`, `APP_CATEGORIES`
  - Actualizar `config/__init__.py` para re-exportar `BASE_DIR`, `DATA_DIR` desde `settings`
  - Mantener `config.py` en root como shim: `from config.settings import *`
  - _Requirements: 4_

- [-] 3. Mover archivos de memory/ y actualizar imports
  - Copiar `memory_db.py` → `memory/memory_db.py` con imports corregidos (`from config.settings import DATA_DIR`)
  - Copiar `agent_memory.py` → `memory/agent_memory.py` con imports corregidos
  - Copiar `alisha_memoria_semantica.py` → `memory/alisha_memoria_semantica.py` con imports corregidos
  - Actualizar `memory/__init__.py` para exportar `MemoryDB`, `get_memory`, `get_indice`
  - Crear shims en root: `memory_db.py`, `agent_memory.py`, `alisha_memoria_semantica.py` con `from memory.X import *`
  - _Requirements: 1, 8_

- [x] 4. Mover archivos de personality/ y actualizar imports
  - Copiar `alisha_identity.py` → `personality/alisha_identity.py` con imports corregidos
  - Copiar `skepticism_engine.py` → `personality/skepticism_engine.py` con imports corregidos
  - Copiar `alisha_curiosidad.py` → `personality/alisha_curiosidad.py` con imports corregidos
  - Actualizar `personality/__init__.py` para exportar `SemillaPersonalidad`, `GestosNoVerbales`, `SkepticismEngine`, `iniciar_curiosidad`
  - Crear shims en root para los 3 archivos movidos
  - _Requirements: 1, 8_

- [ ] 5. Mover archivos de vision/ y tools/
  - Copiar `vision_engine.py` → `vision/vision_engine.py`, `screen_vision.py` → `vision/screen_vision.py`, `context_monitor.py` → `vision/context_monitor.py` con imports corregidos
  - Actualizar `vision/__init__.py` para exportar `get_vision_engine`, `enrich_query_with_vision`, `detectar_rol`
  - Copiar `tools.py` → `tools/tools.py`, `pc_controller.py` → `tools/pc_controller.py`, `natural_mouse.py` → `tools/natural_mouse.py`, `safety_guard.py` → `tools/safety_guard.py` con imports corregidos
  - Actualizar `tools/__init__.py` para exportar `abort_all_actions`, `iniciar_hotkey_bloqueo`, `esta_bloqueado`
  - Crear shims en root para todos los archivos movidos
  - _Requirements: 1, 3, 8_

- [~] 6. Mover archivos de avatar/
  - Copiar `tts_engine.py` → `avatar/tts_engine.py`, `audio_visual_sync.py` → `avatar/audio_visual_sync.py`, `alisha_bridge.py` → `avatar/alisha_bridge.py`, `cabina_virtual.py` → `avatar/cabina_virtual.py` con imports corregidos
  - Verificar que ningún archivo en `avatar/` importa de `core/` — si lo hace, reemplazar con lectura de `data/chibi_state.json`
  - Actualizar `avatar/__init__.py` para exportar `get_audio_visual_sync`, `start_idle_loop`, `speak`
  - Crear shims en root para los archivos movidos
  - _Requirements: 1, 3, 8_

- [~] 7. Extraer clientes LLM a services/
  - Crear `services/ollama_client.py` con clase `OllamaClient` extraída de `brain.py` — métodos `is_available() -> bool` y `chat(messages, **kwargs) -> str`
  - Crear `services/openai_client.py` con clase `OpenAIClient` extraída de `brain.py`
  - Crear `services/groq_client.py` con clase `GroqClient` extraída de `brain.py`
  - Crear `services/gemini_client.py` con clase `GeminiClient` extraída de `brain.py`
  - Crear `services/mistral_client.py` con clase `MistralClient` extraída de `brain.py`
  - Actualizar `services/__init__.py` para exportar los 5 clientes
  - Actualizar `brain.py` para importar clientes desde `services/` en lugar de definirlos localmente
  - _Requirements: 2, 3_

- [~] 8. Dividir brain.py en core/
  - Crear `personality/mood_engine.py` con `PersonalitySynthesizer` extraída de `brain.py` — recibe `EmotionalState` como parámetro, NO importa `EmotionEngine` de `core/`
  - Crear `core/neural_bridge.py` con `MicroGestureEngine` y `SarcasmScoreEngine` extraídas de `brain.py`
  - Crear `core/orchestrator.py` con `IdleWatcher` y lógica de orquestación extraída de `brain.py`
  - Refactorizar `core/brain.py` para contener solo: dataclasses, `ConnectivityChecker`, `SmartRouter`, `UnifiedMemory`, `HybridIntelligenceCore`, `get_brain()` — máximo 300 líneas
  - Actualizar `core/__init__.py` para exportar `HybridIntelligenceCore`, `EmotionEngine`, `get_brain`
  - _Requirements: 2, 9_

- [~] 9. Dividir agent_loop.py en core/
  - Crear `core/screen_watcher.py` con `ScreenWatcher` y `StateMapper` extraídas de `agent_loop.py`
  - Crear `core/assistant_state.py` con helpers `_read_state`, `_write_state`, `_update_state`, `cargar_estado`, `actualizar_estado`
  - Refactorizar `core/agent_loop.py` para contener solo `EventBus` y `AgentLoop` — máximo 300 líneas, importar `ScreenWatcher` desde `core/screen_watcher.py`
  - Mover constantes de `agent_loop.py` a `config/constants.py`
  - Actualizar `core/__init__.py` para exportar `AgentLoop`, `EventBus`
  - Crear shim en root: `agent_loop.py` con `from core.agent_loop import *`
  - _Requirements: 1, 9_

- [~] 10. Dividir web_app.py en web/routes/
  - Crear `web/helpers.py` con funciones auxiliares: `_detectar_accion_fisica`, `_analizar_intencion_y_proponer`, `_map_brain_emotion`, `_ejecutar_accion_fisica`
  - Crear `web/routes/system.py` con endpoints: `/api/perfil`, `/api/historial`, `/api/sesiones`, `/api/status`, `/api/stop`, `/api/reiniciar`, `/api/nuevo_chat`, `/api/lock`, `/api/despertar`, `/api/salud`
  - Crear `web/routes/files.py` con endpoints: `/api/upload`, `/api/analyze-doc`, `/api/generar_imagen`, `/api/brain/status`, `/api/vision/goal`, `/api/vision/snapshot`
  - Crear `web/routes/chat.py` con endpoints: `/api/audio`, `/api/test_mouse`, `/api/escribir_en`, `/api/confirmar_accion`, y el handler WebSocket `@socketio.on("mensaje")`
  - Crear `web/routes/config_routes.py` con endpoints: `/api/config` (GET/POST), `/api/config/reset`, `/config`, `/`, `/landing`
  - Crear `web/routes/extras.py` con endpoints: `/api/trust`, `/api/imprimir/*`, `/api/entrenar`, `/api/habilidades`, `/api/sugerencia/rechazar`
  - Refactorizar `web/web_app.py` como app factory: crear `app`, `socketio`, `_inicializar()`, registrar blueprints
  - Crear shim en root: `web_app.py` con `from web.web_app import app, socketio, _inicializar`
  - _Requirements: 6, 9_

- [~] 11. Crear main.py como único punto de entrada
  - Crear `main.py` con función `main()` que inicializa config, inicia watchdog del servidor web, inicia Live2D, inicia sistema de sueño, inicia tray icon
  - Implementar single-instance lock (archivo `.lock` con PID, verificación con psutil)
  - Implementar watchdog de auto-restart (máx 10 intentos, 3s de espera)
  - Implementar `--install` y `--remove` para autostart de Windows
  - Implementar crash logger que escribe en `data/crash_log.txt`
  - Actualizar `Alisha_IA.py` como shim: `from main import main`
  - _Requirements: 5_

- [~] 12. Crear integrations/ con estructura base
  - Crear `integrations/discord_bot.py` con clase `DiscordBot(start, stop)` — métodos vacíos (pass), docstring descriptivo
  - Crear `integrations/telegram_bot.py` con clase `TelegramBot(start, stop)`
  - Crear `integrations/whatsapp_bridge.py` con clase `WhatsAppBridge(start, stop)`
  - Crear `integrations/youtube_client.py` con clase `YouTubeClient(start, stop)`
  - Actualizar `integrations/__init__.py` con `get_available_integrations() -> list[str]`
  - _Requirements: 7_

- [~] 13. Verificar arranque completo y actualizar __init__.py
  - Actualizar `core/__init__.py` para exportar: `HybridIntelligenceCore`, `AgentLoop`, `EmotionEngine`, `EventBus`, `get_brain`
  - Actualizar `memory/__init__.py` para exportar: `MemoryDB`, `get_memory`, `get_indice`
  - Actualizar `personality/__init__.py` para exportar: `PersonalitySynthesizer`, `SemillaPersonalidad`, `GestosNoVerbales`, `SkepticismEngine`, `iniciar_curiosidad`
  - Actualizar `services/__init__.py` para exportar: `GeminiClient`, `GroqClient`, `OpenAIClient`, `OllamaClient`, `MistralClient`
  - Verificar que `python main.py` arranca sin `ImportError` ni `ModuleNotFoundError`
  - Ejecutar la suite de tests existente en `tests/` y verificar que pasa
  - _Requirements: 8, 10_
